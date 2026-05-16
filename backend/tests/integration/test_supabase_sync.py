"""
Integration tests for Supabase sync service
"""

from backend.services.supabase_sync import SupabaseSyncService


class TestSupabaseSync:
    """Pruebas del servicio de sincronizacion Supabase"""

    def test_supabase_sync_service_imports(self):
        assert SupabaseSyncService is not None

    def test_supabase_sync_service_instance(self):
        service = SupabaseSyncService()
        assert hasattr(service, "enabled")
        assert hasattr(service, "sync_debate")
        assert hasattr(service, "sync_reductio_proofs")
        assert hasattr(service, "get_debate_from_cloud")
        assert hasattr(service, "list_debates_from_cloud")

    def test_supabase_sync_reductio_proofs_method_signature(self):
        service = SupabaseSyncService()
        import inspect

        sig = inspect.signature(service.sync_reductio_proofs)
        params = list(sig.parameters.keys())
        assert "debate_id" in params
        assert "proofs" in params
