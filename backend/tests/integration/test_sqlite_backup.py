"""
Integration tests for SQLite backup service
"""
from backend.services.sqlite_backup import SQLiteBackupService, get_backup_service


class TestSQLiteBackup:
    """Pruebas del servicio de backup SQLite"""

    def test_backup_service_imports(self):
        assert SQLiteBackupService is not None
        assert get_backup_service is not None

    def test_backup_service_instance(self):
        service = SQLiteBackupService()
        assert hasattr(service, "enabled")
        assert hasattr(service, "create_backup")
        assert hasattr(service, "list_backups")
        assert hasattr(service, "delete_backup")
        assert hasattr(service, "restore_backup")
        assert hasattr(service, "BACKUP_BUCKET")

    def test_backup_service_singleton(self):
        service1 = get_backup_service()
        service2 = get_backup_service()
        assert service1 is service2

    def test_backup_service_bucket_name(self):
        service = SQLiteBackupService()
        assert service.BACKUP_BUCKET == "synapse-backups"

    def test_backup_service_has_db_path(self):
        service = SQLiteBackupService()
        assert hasattr(service, "db_path")
