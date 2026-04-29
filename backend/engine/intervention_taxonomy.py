"""
Taxonomía de Intervenciones - Sistema de clasificación de actos discursivos.
Adaptado de CORAL v5.3 para Synapse Council v2.0.
"""

from enum import Enum
from typing import List


class TipoIntervencion(Enum):
    """Tipos de intervenciones en un debate."""
    APERTURA = 'apertura'
    ARGUMENTO = 'argumento'
    CONTRAARGUMENTO = 'contraargumento'
    REFUTACION = 'refutacion'
    PREGUNTA = 'pregunta'
    CONSENSO = 'consenso'
    SINTESIS = 'sintesis'
    CRITICA = 'critica'
    VALIDACION = 'validacion'
    DESCONOCIDO = 'desconocido'


class InterventionDetector:
    """
    Detector heurístico de tipo de intervención basado en palabras clave.
    Prioridad: refutación > consenso > pregunta > por_rol.
    """
    
    # Palabras clave para cada tipo (en español)
    REFUTACION_KW = [
        'sin embargo', 'contradice', 'incorrecto', 'error en',
        'no es cierto', 'refuto', 'contradigo', 'no coincide',
        'estoy en desacuerdo', 'discrepo', 'no estoy de acuerdo'
    ]
    
    CONSENSO_KW = [
        'coincido', 'de acuerdo', 'consenso', 'todos coinciden',
        'convergencia', 'coincidimos', 'comparto', 'acepto',
        'estoy de acuerdo', 'concuerdo', 'convergimos'
    ]
    
    PREGUNTA_KW = [
        '¿por qué', '¿cómo', '¿qué evidencia', 'me pregunto',
        'no queda claro', '¿es posible', '¿podría', 'duda',
        'interrogante', 'cuestiono', '¿dónde', '¿cuándo'
    ]
    
    CRITICA_KW = [
        'debilidad', 'fallo', 'problema con', 'insuficiente',
        'no considera', 'omite', 'sesgado', 'cuestionable',
        'limitación', 'deficiencia', 'mejorable', 'incompleto'
    ]
    
    def detect(self, content: str, role: str) -> TipoIntervencion:
        """
        Detecta el tipo de intervención basado en contenido y rol.
        
        Args:
            content: Texto de la respuesta del agente
            role: Rol del agente (analyst, critic, synthesizer, etc.)
            
        Returns:
            TipoIntervencion detectado
        """
        if not content:
            return TipoIntervencion.DESCONOCIDO
            
        cl = content.lower()
        
        # Prioridad 1: Refutación (más específico)
        if sum(1 for kw in self.REFUTACION_KW if kw in cl) >= 2:
            return TipoIntervencion.REFUTACION
            
        # Prioridad 2: Consenso
        if sum(1 for kw in self.CONSENSO_KW if kw in cl) >= 2:
            return TipoIntervencion.CONSENSO
            
        # Prioridad 3: Pregunta
        if any(kw in cl for kw in self.PREGUNTA_KW):
            return TipoIntervencion.PREGUNTA
        
        # Por rol (fallback)
        if role == 'critic':
            has_critica = sum(1 for kw in self.CRITICA_KW if kw in cl) >= 1
            return TipoIntervencion.REFUTACION if has_critica else TipoIntervencion.CRITICA
        if role == 'synthesizer':
            return TipoIntervencion.SINTESIS
        if role in ('analyst', 'refiner'):
            return TipoIntervencion.ARGUMENTO
        if role == 'moderator':
            return TipoIntervencion.VALIDACION
            
        return TipoIntervencion.DESCONOCIDO
    
    def build_summary(self, turns: list) -> dict:
        """
        Construye resumen estadístico de tipos de intervención.
        
        Args:
            turns: Lista de turnos del debate
            
        Returns:
            Dict con conteos y ratios
        """
        counts = {t.value: 0 for t in TipoIntervencion}
        
        for turn in turns:
            it = getattr(turn, 'intervention_type', 'desconocido')
            counts[it] = counts.get(it, 0) + 1
            
        total = max(sum(counts.values()), 1)
        
        return {
            'by_type': counts,
            'consensus_ratio': counts.get('consenso', 0) / total,
            'conflict_ratio': (counts.get('refutacion', 0) + counts.get('critica', 0)) / total,
            'total_analyzed': total
        }


# Instancia global para uso directo
detector = InterventionDetector()


def detect_intervention_type(content: str, role: str) -> str:
    """
    Función helper para detectar tipo de intervención.
    Reseta feature flag INTERVENTION_TAXONOMY_ENABLED.
    """
    try:
        from backend.config import settings
        if not getattr(settings, 'INTERVENTION_TAXONOMY_ENABLED', True):
            return 'desconocido'
        return detector.detect(content, role).value
    except Exception:
        return 'desconocido'
