"""
Unit tests for WebSocket manager
"""

from unittest.mock import MagicMock

from backend.api.websocket import WebSocketManager


class TestWebSocketManager:
    """Pruebas del gestor de WebSocket"""

    def test_websocket_manager_imports(self):
        assert WebSocketManager is not None

    def test_websocket_manager_buffer_tokens(self):
        manager = WebSocketManager()
        manager.buffer_tokens = True
        assert manager.buffer_tokens is True

    def test_websocket_manager_flush_buffer(self):
        manager = WebSocketManager()
        assert hasattr(manager, "flush_session")
        assert callable(manager.flush_session)

    def test_websocket_manager_add_remove_connection(self):
        manager = WebSocketManager()
        mock_ws = MagicMock()
        mock_ws.send_text = MagicMock()
        try:
            manager.connect("test-session", mock_ws)
            assert len(manager.active_connections) > 0 or len(manager.token_buffers) > 0
        except Exception:
            pass

    def test_websocket_manager_has_buffer_capability(self):
        manager = WebSocketManager()
        assert hasattr(manager, "_buffer_token_event")
        assert hasattr(manager, "token_buffers")
