"""
SynapseCode - SQLite Backup Service
Automatic backup of SQLite database to Supabase Storage
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import structlog

from backend.adapters.http_client_manager import ClientConfig, HTTPClientManager
from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class SQLiteBackupService:
    """
    Servicio de backup de SQLite a Supabase Storage.
    Crea copias de seguridad de la base de datos y las sube a Supabase Storage.
    """

    SERVICE_NAME = "supabase_storage"
    BACKUP_BUCKET = "synapse-backups"

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_ANON_KEY
        self.service_key = getattr(settings, "SUPABASE_SERVICE_KEY", None) or self.key
        is_placeholder = (
            "CHANGEME" in (self.url or "")
            or "CHANGEME" in (self.key or "")
            or not self.url
            or not self.key
        )
        self.enabled = settings.SUPABASE_ENABLED and not is_placeholder
        self.db_path = (
            settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace(
                "sqlite:///", ""
            )
            if settings.DATABASE_URL
            else ""
        )

    def _get_storage_client(self) -> httpx.AsyncClient:
        """Obtiene cliente HTTP para Supabase Storage"""
        config = ClientConfig(
            timeout=60.0,
            headers={
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": "application/octet-stream",
            },
        )
        return HTTPClientManager.get_client(self.SERVICE_NAME, config=config)

    async def _ensure_bucket_exists(self) -> bool:
        """Verifica/crea el bucket de backups en Supabase Storage"""
        if not self.enabled:
            return False

        try:
            client = self._get_storage_client()
            # Listar buckets para verificar si existe
            response = await client.get(
                f"{self.url}/storage/v1/bucket",
                headers={"Authorization": f"Bearer {self.service_key}"},
            )

            if response.status_code == 200:
                buckets = response.json()
                bucket_names = [b.get("name") for b in buckets]
                if self.BACKUP_BUCKET in bucket_names:
                    return True

                # Crear bucket si no existe
                create_response = await client.post(
                    f"{self.url}/storage/v1/bucket",
                    json={
                        "name": self.BACKUP_BUCKET,
                        "public": False,
                        "file_size_limit": 52428800,  # 50MB
                    },
                    headers={
                        "Authorization": f"Bearer {self.service_key}",
                        "Content-Type": "application/json",
                    },
                )

                if create_response.status_code in [200, 201]:
                    logger.info(
                        "supabase_storage.bucket_created", bucket=self.BACKUP_BUCKET
                    )
                    return True
                elif "already exists" in create_response.text.lower():
                    return True
                else:
                    logger.warning(
                        "supabase_storage.bucket_create_failed",
                        status=create_response.status_code,
                        error=create_response.text,
                    )
                    return False

            return False

        except Exception as e:
            logger.error("supabase_storage.bucket_check_failed", error=str(e))
            return False

    async def create_backup(self) -> Dict[str, Any]:
        """
        Crea un backup de la base de datos SQLite y lo sube a Supabase Storage.

        Returns:
            Dict con resultado del backup
        """
        if not self.enabled:
            return {"success": False, "reason": "Supabase not enabled"}

        if not self.db_path or not Path(self.db_path).exists():
            return {
                "success": False,
                "reason": f"Database file not found: {self.db_path}",
            }

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"synapse_{timestamp}.db"
        backup_path = None

        try:
            # Crear copia temporal de la base de datos
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                backup_path = tmp.name
                shutil.copy2(self.db_path, backup_path)

            # Verificar que el bucket existe
            bucket_ready = await self._ensure_bucket_exists()
            if not bucket_ready:
                return {
                    "success": False,
                    "reason": "Could not create/verify backup bucket",
                }

            # Subir a Supabase Storage
            client = self._get_storage_client()
            with open(backup_path, "rb") as f:
                db_content = f.read()

            upload_response = await client.post(
                f"{self.url}/storage/v1/object/{self.BACKUP_BUCKET}/{backup_filename}",
                content=db_content,
                headers={
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/octet-stream",
                    "x-upsert": "true",
                },
            )

            if upload_response.status_code in [200, 201]:
                file_size = len(db_content)
                logger.info(
                    "supabase_storage.backup_uploaded",
                    filename=backup_filename,
                    size_bytes=file_size,
                )

                return {
                    "success": True,
                    "filename": backup_filename,
                    "bucket": self.BACKUP_BUCKET,
                    "size_bytes": file_size,
                    "timestamp": timestamp,
                    "url": f"{self.url}/storage/v1/object/{self.BACKUP_BUCKET}/{backup_filename}",
                }
            else:
                logger.error(
                    "supabase_storage.upload_failed",
                    status=upload_response.status_code,
                    error=upload_response.text,
                )
                return {"success": False, "error": upload_response.text}

        except Exception as e:
            logger.error("supabase_storage.backup_exception", error=str(e))
            return {"success": False, "error": str(e)}

        finally:
            # Limpiar archivo temporal
            if backup_path and Path(backup_path).exists():
                try:
                    os.remove(backup_path)
                except OSError:
                    pass

    async def list_backups(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Lista los backups disponibles en Supabase Storage.

        Args:
            limit: Numero maximo de backups a retornar

        Returns:
            Lista de backups con metadata
        """
        if not self.enabled:
            return []

        try:
            client = self._get_storage_client()
            response = await client.post(
                f"{self.url}/storage/v1/object/list/{self.BACKUP_BUCKET}",
                json={
                    "prefix": "",
                    "limit": limit,
                    "sortBy": {"column": "created_at", "order": "desc"},
                },
                headers={
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                files = response.json()
                return [
                    {
                        "name": f.get("name"),
                        "size": f.get("metadata", {}).get("size", 0),
                        "created_at": f.get("created_at"),
                        "updated_at": f.get("updated_at"),
                    }
                    for f in files
                    if f.get("name", "").endswith(".db")
                ]

            logger.warning("supabase_storage.list_failed", status=response.status_code)
            return []

        except Exception as e:
            logger.error("supabase_storage.list_exception", error=str(e))
            return []

    async def delete_backup(self, filename: str) -> Dict[str, Any]:
        """
        Elimina un backup especifico de Supabase Storage.

        Args:
            filename: Nombre del archivo a eliminar

        Returns:
            Dict con resultado de la eliminacion
        """
        if not self.enabled:
            return {"success": False, "reason": "Supabase not enabled"}

        try:
            client = self._get_storage_client()
            response = await client.delete(
                f"{self.url}/storage/v1/object/{self.BACKUP_BUCKET}/{filename}",
                headers={"Authorization": f"Bearer {self.service_key}"},
            )

            if response.status_code in [200, 204]:
                logger.info("supabase_storage.backup_deleted", filename=filename)
                return {"success": True, "filename": filename}
            else:
                return {"success": False, "error": response.text}

        except Exception as e:
            logger.error("supabase_storage.delete_exception", error=str(e))
            return {"success": False, "error": str(e)}

    async def restore_backup(self, filename: str) -> Dict[str, Any]:
        """
        Descarga un backup de Supabase Storage (no restaura automaticamente).

        Args:
            filename: Nombre del archivo a descargar

        Returns:
            Dict con resultado y path del archivo descargado
        """
        if not self.enabled:
            return {"success": False, "reason": "Supabase not enabled"}

        download_path = None

        try:
            client = self._get_storage_client()
            response = await client.get(
                f"{self.url}/storage/v1/object/{self.BACKUP_BUCKET}/{filename}"
            )

            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                    tmp.write(response.content)
                    download_path = tmp.name

                logger.info(
                    "supabase_storage.backup_downloaded",
                    filename=filename,
                    size_bytes=len(response.content),
                )

                return {
                    "success": True,
                    "filename": filename,
                    "download_path": download_path,
                    "size_bytes": len(response.content),
                    "message": "Backup downloaded. Manual restore required.",
                }
            else:
                return {"success": False, "error": response.text}

        except Exception as e:
            if download_path and Path(download_path).exists():
                os.remove(download_path)
            logger.error("supabase_storage.restore_exception", error=str(e))
            return {"success": False, "error": str(e)}

    async def close(self):
        """Cierra conexion HTTP"""
        await HTTPClientManager.close(self.SERVICE_NAME)


# Singleton instance
_backup_service: Optional[SQLiteBackupService] = None


def get_backup_service() -> SQLiteBackupService:
    """Obtiene instancia singleton del servicio de backup"""
    global _backup_service
    if _backup_service is None:
        _backup_service = SQLiteBackupService()
    return _backup_service
