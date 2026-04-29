"""
Quality Monitor - Evaluación de calidad de respuestas de agentes.
Filtra respuestas de baja calidad del contexto.
"""

from typing import List, Tuple
import structlog

logger = structlog.get_logger()


class QualityMonitor:
    """
    Evalúa calidad de respuestas generadas por agentes.
    Detecta: respuestas cortas, sin formato esperado, truncadas.
    """
    
    MIN_LENGTH = 80  # Caracteres mínimos
    
    # Palabras clave esperadas por rol
    EXPECTED = {
        'analyst': ['análisis', 'posición', 'argumento', 'evidencia'],
        'critic': ['validaci', 'crítica', 'veredicto', 'evaluación'],
        'synthesizer': ['síntesis', 'convergencia', 'consenso', 'integración'],
        'refiner': ['refinamiento', 'argumento', 'mejora'],
        'moderator': ['veredicto', 'fundamento', 'conclusión'],
    }
    
    def evaluate(self, content: str, role: str) -> Tuple[float, List[str]]:
        """
        Evalúa calidad de una respuesta.
        
        Args:
            content: Texto de la respuesta
            role: Rol del agente
            
        Returns:
            Tuple (score 0.0-1.0, lista de issues)
        """
        if not content:
            return 0.0, ['Respuesta vacía']
        
        issues = []
        score = 1.0
        
        # Check 1: Longitud mínima
        if len(content) < self.MIN_LENGTH:
            issues.append(f'Muy corta: {len(content)} chars (min {self.MIN_LENGTH})')
            score -= 0.5
        
        # Check 2: Secciones esperadas
        expected_keywords = self.EXPECTED.get(role, [])
        missing = [s for s in expected_keywords if s not in content.lower()]
        if missing:
            issues.append(f'Sin secciones esperadas: {missing}')
            score -= 0.15 * len(missing)
        
        # Check 3: Posiblemente truncada
        content_stripped = content.strip()
        if content_stripped and content_stripped[-1] not in '.!?}]"\'':
            issues.append('Posiblemente truncada (no termina en puntuación)')
            score -= 0.1
        
        # Check 4: Patrones de error comunes
        error_patterns = ['error', 'falló', 'timeout', 'no disponible', 'exception']
        for pattern in error_patterns:
            if pattern in content.lower() and len(content) < 200:
                issues.append(f'Posible mensaje de error: {pattern}')
                score -= 0.3
                break
        
        final_score = max(0.0, min(1.0, score))
        
        if final_score < 0.4:
            logger.warning('quality_monitor.low_quality',
                        role=role,
                        score=round(final_score, 2),
                        length=len(content),
                        issues=issues)
        
        return final_score, issues
    
    def is_usable(self, content: str, role: str) -> bool:
        """
        Determina si una respuesta es usable en el contexto.
        
        Args:
            content: Texto de la respuesta
            role: Rol del agente
            
        Returns:
            True si score >= 0.4
        """
        score, _ = self.evaluate(content, role)
        return score >= 0.4
    
    def summary(self, turns: list) -> dict:
        """
        Genera resumen de calidad de todos los turnos.
        
        Args:
            turns: Lista de turnos
            
        Returns:
            Dict con estadísticas de calidad
        """
        scores = []
        low_quality_count = 0
        
        for turn in turns:
            response = getattr(turn, 'response_received', '')
            role = getattr(getattr(turn, 'agent', None), 'role', None)
            role_value = getattr(role, 'value', 'unknown') if role else 'unknown'
            
            if response and hasattr(turn, 'status'):
                status = getattr(turn, 'status', '')
                if isinstance(status, str) and status.startswith('completed'):
                    score, _ = self.evaluate(response, role_value)
                    scores.append(score)
                    if score < 0.4:
                        low_quality_count += 1
        
        if not scores:
            return {'avg': 0.0, 'min': 0.0, 'low_quality': 0, 'total': 0}
        
        return {
            'avg': round(sum(scores) / len(scores), 3),
            'min': round(min(scores), 3),
            'max': round(max(scores), 3),
            'low_quality': low_quality_count,
            'total': len(scores)
        }


# Instancia global
quality_monitor = QualityMonitor()


def evaluate_response(content: str, role: str) -> Tuple[float, List[str]]:
    """Helper simple para evaluar una respuesta."""
    try:
        return quality_monitor.evaluate(content, role)
    except Exception as e:
        logger.error('quality_monitor.error', error=str(e))
        return 0.5, ['Error en evaluación']


def is_response_usable(content: str, role: str) -> bool:
    """Helper simple para verificar si respuesta es usable."""
    try:
        from backend.config import settings
        if not getattr(settings, 'QUALITY_MONITOR_ENABLED', True):
            return True  # Feature desactivada, asumir usable
        return quality_monitor.is_usable(content, role)
    except Exception:
        return True  # Fallback: asumir usable si hay error
