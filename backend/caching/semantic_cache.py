"""
SynapseCode Semantic Cache Service
Caché semántica de respuestas usando embeddings y similitud coseno
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import structlog
from sqlalchemy import and_, func, or_, select

from backend.config import get_settings
from backend.database.local_db import AsyncSessionLocal
from backend.database.models import PromptResponseCache
from backend.monitoring.prometheus import (
    record_prompt_cache_hit,
    record_prompt_cache_miss,
)

logger = structlog.get_logger()
settings = get_settings()


class SemanticCacheService:
    """
    Servicio de caché semántica basado en embeddings.
    Busca respuestas similares por similitud coseno.
    """

    def __init__(self):
        self._embedding_model = None
        self._embedding_dimension = 384  # sentence-transformers/all-MiniLM-L6-v2
        self._cache_ttl_hours = (
            settings.SEMANTIC_CACHE_TTL_HOURS if hasattr(settings, "SEMANTIC_CACHE_TTL_HOURS") else 24
        )
        self._similarity_threshold = (
            settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD
            if hasattr(settings, "SEMANTIC_CACHE_SIMILARITY_THRESHOLD")
            else 0.85
        )
        self._enabled = settings.SEMANTIC_CACHE_ENABLED if hasattr(settings, "SEMANTIC_CACHE_ENABLED") else True

    def _get_embedding_model(self):
        """Lazy loading del modelo de embeddings (sentence-transformers)"""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("semantic_cache.embedding_model_loaded", model="all-MiniLM-L6-v2")
            except ImportError:
                logger.warning(
                    "semantic_cache.sentence_transformers_not_installed",
                    fallback="hash_based",
                )
                self._enabled = False
        return self._embedding_model

    def _generate_embedding(self, text: str) -> list[float] | None:
        """Genera embedding del texto usando sentence-transformers"""
        if not self._enabled:
            return None

        try:
            model = self._get_embedding_model()
            if model is None:
                return None

            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error("semantic_cache.embedding_failed", error=str(e))
            return None

    def _cosine_similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """Calcula similitud coseno entre dos embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
        except Exception as e:
            logger.error("semantic_cache.similarity_failed", error=str(e))
            return 0.0

    def _generate_cache_key(self, prompt: str, model: str, temperature: float, max_tokens: int | None) -> str:
        """Genera clave única para caché basada en configuración"""
        key_parts = [
            prompt,
            model,
            str(temperature),
            str(max_tokens) if max_tokens else "None",
        ]
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    async def get(
        self,
        prompt: str,
        model: str,
        engine: str,
        node: str = "LOCAL",
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> dict[str, Any] | None:
        """
        Busca respuesta en caché semántica.
        Devuelve la respuesta más similar si supera el threshold.
        """
        if not self._enabled:
            record_prompt_cache_miss("semantic")
            return None

        try:
            # Generar embedding del prompt
            prompt_embedding = self._generate_embedding(prompt)
            if not prompt_embedding:
                record_prompt_cache_miss("semantic")
                return None

            async with AsyncSessionLocal() as db:
                # Buscar entradas válidas del mismo modelo/engine
                now = datetime.now(UTC)
                query = select(PromptResponseCache).where(
                    and_(
                        PromptResponseCache.engine == engine,
                        PromptResponseCache.model == model,
                        PromptResponseCache.node == node,
                        PromptResponseCache.temperature == temperature,
                        PromptResponseCache.max_tokens == max_tokens,
                        or_(
                            PromptResponseCache.expires_at.is_(None),
                            PromptResponseCache.expires_at > now,
                        ),
                        PromptResponseCache.prompt_embedding.isnot(None),
                    )
                )
                result = await db.execute(query)
                cache_entries = result.scalars().all()

                # Buscar la más similar
                best_match = None
                best_similarity = 0.0

                for entry in cache_entries:
                    if entry.prompt_embedding:
                        try:
                            entry_embedding = json.loads(entry.prompt_embedding)
                            similarity = self._cosine_similarity(prompt_embedding, entry_embedding)

                            if similarity > best_similarity and similarity >= self._similarity_threshold:
                                best_similarity = similarity
                                best_match = entry
                        except Exception as e:
                            logger.warning(
                                "semantic_cache.entry_parse_failed",
                                entry_id=entry.id,
                                error=str(e),
                            )
                            continue

                if best_match:
                    # Actualizar hit_count y last_accessed_at
                    best_match.hit_count += 1
                    best_match.last_accessed_at = now
                    await db.commit()

                    logger.info(
                        "semantic_cache.hit",
                        cache_id=best_match.id,
                        similarity=best_similarity,
                        hit_count=best_match.hit_count,
                    )
                    record_prompt_cache_hit("semantic")

                    return {
                        "response_text": best_match.response_text,
                        "tokens_in": best_match.tokens_in,
                        "tokens_out": best_match.tokens_out,
                        "latency_ms": best_match.latency_ms,
                        "from_cache": True,
                        "similarity": best_similarity,
                    }

                logger.debug(
                    "semantic_cache.miss",
                    model=model,
                    entries_checked=len(cache_entries),
                )
                record_prompt_cache_miss("semantic")
                return None

        except Exception as e:
            logger.error("semantic_cache.get_failed", error=str(e))
            record_prompt_cache_miss("semantic")
            return None

    async def set(
        self,
        prompt: str,
        response_text: str,
        model: str,
        engine: str,
        node: str = "LOCAL",
        temperature: float = 0.0,
        max_tokens: int | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int = 0,
    ) -> bool:
        """
        Guarda respuesta en caché semántica.
        """
        if not self._enabled:
            return False

        try:
            cache_key = self._generate_cache_key(prompt, model, temperature, max_tokens)
            prompt_embedding = self._generate_embedding(prompt)

            if not prompt_embedding:
                # Fallback: guardar sin embedding (caché determinista)
                prompt_embedding = None

            # Calcular expiración
            expires_at = datetime.now(UTC) + timedelta(hours=self._cache_ttl_hours)

            async with AsyncSessionLocal() as db:
                # Verificar si ya existe
                existing = await db.execute(
                    select(PromptResponseCache).where(PromptResponseCache.cache_key == cache_key)
                )
                existing_entry = existing.scalar_one_or_none()

                if existing_entry:
                    # Actualizar entrada existente
                    existing_entry.response_text = response_text
                    existing_entry.tokens_in = tokens_in
                    existing_entry.tokens_out = tokens_out
                    existing_entry.latency_ms = latency_ms
                    existing_entry.last_accessed_at = datetime.now(UTC)
                    existing_entry.expires_at = expires_at
                    if prompt_embedding:
                        existing_entry.prompt_embedding = json.dumps(prompt_embedding)
                else:
                    # Crear nueva entrada
                    cache_entry = PromptResponseCache(
                        cache_key=cache_key,
                        engine=engine,
                        model=model,
                        node=node,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
                        prompt_embedding=json.dumps(prompt_embedding) if prompt_embedding else None,
                        response_text=response_text,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        latency_ms=latency_ms,
                        hit_count=0,
                        similarity_threshold=self._similarity_threshold,
                        expires_at=expires_at,
                    )
                    db.add(cache_entry)

                await db.commit()
                logger.info(
                    "semantic_cache.set",
                    cache_key=cache_key,
                    has_embedding=prompt_embedding is not None,
                )
                return True

        except Exception as e:
            logger.error("semantic_cache.set_failed", error=str(e))
            return False

    async def invalidate(self, model: str | None = None, engine: str | None = None) -> int:
        """
        Invalida entradas de caché por modelo/engine.
        Devuelve número de entradas eliminadas.
        """
        try:
            async with AsyncSessionLocal() as db:
                query = select(PromptResponseCache)
                conditions = []

                if model:
                    conditions.append(PromptResponseCache.model == model)
                if engine:
                    conditions.append(PromptResponseCache.engine == engine)

                if conditions:
                    query = query.where(and_(*conditions))

                result = await db.execute(query)
                entries = result.scalars().all()

                count = len(entries)
                for entry in entries:
                    await db.delete(entry)

                await db.commit()
                logger.info(
                    "semantic_cache.invalidated",
                    count=count,
                    model=model,
                    engine=engine,
                )
                return count

        except Exception as e:
            logger.error("semantic_cache.invalidate_failed", error=str(e))
            return 0

    async def cleanup_expired(self) -> int:
        """
        Elimina entradas expiradas de caché.
        Devuelve número de entradas eliminadas.
        """
        try:
            async with AsyncSessionLocal() as db:
                now = datetime.now(UTC)
                query = select(PromptResponseCache).where(PromptResponseCache.expires_at < now)
                result = await db.execute(query)
                entries = result.scalars().all()

                count = len(entries)
                for entry in entries:
                    await db.delete(entry)

                await db.commit()
                logger.info("semantic_cache.cleanup", count=count)
                return count

        except Exception as e:
            logger.error("semantic_cache.cleanup_failed", error=str(e))
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """
        Devuelve estadísticas de la caché.
        """
        try:
            async with AsyncSessionLocal() as db:
                # Total entries
                total_result = await db.execute(select(func.count(PromptResponseCache.id)))
                total = total_result.scalar()

                # Total hits
                hits_result = await db.execute(select(func.sum(PromptResponseCache.hit_count)))
                total_hits = hits_result.scalar() or 0

                # Entries with embeddings
                with_embeddings_result = await db.execute(
                    select(func.count(PromptResponseCache.id)).where(PromptResponseCache.prompt_embedding.isnot(None))
                )
                with_embeddings = with_embeddings_result.scalar()

                return {
                    "total_entries": total,
                    "total_hits": total_hits,
                    "entries_with_embeddings": with_embeddings,
                    "hit_rate": (total_hits / total) if total > 0 else 0.0,
                    "enabled": self._enabled,
                    "similarity_threshold": self._similarity_threshold,
                    "ttl_hours": self._cache_ttl_hours,
                }

        except Exception as e:
            logger.error("semantic_cache.stats_failed", error=str(e))
            return {"error": str(e), "enabled": self._enabled}


# Instancia global
semantic_cache = SemanticCacheService()
