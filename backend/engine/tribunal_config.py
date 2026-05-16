"""
Configurable Tribunal magistrate profiles.

Keeps TribunalCouncil focused on deliberation while this module owns role
configuration, environment overrides and fallback chains.
"""
from dataclasses import dataclass
from typing import Dict, Iterable, List

from backend.config import Settings, get_settings
from backend.engine.agent_orchestrator import AgentConfig


TRIBUNAL_ROLES = ("evidence", "risk", "alignment")


@dataclass(frozen=True)
class TribunalRoleConfig:
    role: str
    primary: AgentConfig
    fallbacks: List[AgentConfig]

    @property
    def chain(self) -> List[AgentConfig]:
        return [self.primary, *self.fallbacks]


def _agent(
    *,
    slot: str,
    node: str,
    engine: str,
    model: str,
    role_label: str,
    temperature: float,
    max_tokens: int,
) -> AgentConfig:
    return AgentConfig(
        slot=slot,
        node=node,
        engine=engine,
        model=model,
        role_label=role_label,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _cloud_fallback(settings: Settings, role: str, temperature: float, max_tokens: int) -> AgentConfig:
    return _agent(
        slot=f"magistrate_{role}_cloud_fallback",
        node="CLOUD",
        engine=settings.TRIBUNAL_CLOUD_FALLBACK_ENGINE,
        model=settings.TRIBUNAL_CLOUD_FALLBACK_MODEL,
        role_label=f"Magistrado de {role.capitalize()} (Fallback Cloud)",
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _local_reserve(role: str, temperature: float, max_tokens: int) -> AgentConfig:
    return _agent(
        slot=f"magistrate_{role}_local_reserve",
        node="LOCAL",
        engine="ollama",
        model="llama3.2:latest",
        role_label=f"Magistrado de {role.capitalize()} (Reserva Local)",
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _dedupe_chain(configs: Iterable[AgentConfig]) -> List[AgentConfig]:
    seen: set[tuple[str, str, str]] = set()
    deduped: List[AgentConfig] = []
    for config in configs:
        key = (config.node, config.engine, config.model)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(config)
    return deduped


def build_tribunal_config(settings: Settings | None = None) -> Dict[str, TribunalRoleConfig]:
    settings = settings or get_settings()

    role_specs = {
        "evidence": {
            "label": "Magistrado de Evidencias",
            "node": settings.TRIBUNAL_EVIDENCE_NODE,
            "engine": settings.TRIBUNAL_EVIDENCE_ENGINE,
            "model": settings.TRIBUNAL_EVIDENCE_MODEL,
            "temperature": settings.TRIBUNAL_EVIDENCE_TEMPERATURE,
            "max_tokens": settings.TRIBUNAL_EVIDENCE_MAX_TOKENS,
        },
        "risk": {
            "label": "Magistrado de Riesgos",
            "node": settings.TRIBUNAL_RISK_NODE,
            "engine": settings.TRIBUNAL_RISK_ENGINE,
            "model": settings.TRIBUNAL_RISK_MODEL,
            "temperature": settings.TRIBUNAL_RISK_TEMPERATURE,
            "max_tokens": settings.TRIBUNAL_RISK_MAX_TOKENS,
        },
        "alignment": {
            "label": "Magistrado de Alineación",
            "node": settings.TRIBUNAL_ALIGNMENT_NODE,
            "engine": settings.TRIBUNAL_ALIGNMENT_ENGINE,
            "model": settings.TRIBUNAL_ALIGNMENT_MODEL,
            "temperature": settings.TRIBUNAL_ALIGNMENT_TEMPERATURE,
            "max_tokens": settings.TRIBUNAL_ALIGNMENT_MAX_TOKENS,
        },
    }

    role_configs: Dict[str, TribunalRoleConfig] = {}
    for role, spec in role_specs.items():
        primary = _agent(
            slot=f"magistrate_{role}",
            node=spec["node"],
            engine=spec["engine"],
            model=spec["model"],
            role_label=spec["label"],
            temperature=spec["temperature"],
            max_tokens=spec["max_tokens"],
        )
        fallback_candidates = [_local_reserve(role, spec["temperature"], spec["max_tokens"])]
        if settings.TRIBUNAL_ENABLE_CLOUD_FALLBACK:
            fallback_candidates.append(
                _cloud_fallback(settings, role, spec["temperature"], spec["max_tokens"])
            )

        chain = _dedupe_chain([primary, *fallback_candidates])
        role_configs[role] = TribunalRoleConfig(
            role=role,
            primary=chain[0],
            fallbacks=chain[1:],
        )

    return role_configs
