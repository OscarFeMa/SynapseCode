"""
Integration tests for task manager
"""
import asyncio
from backend.engine.task_manager import BackgroundTaskManager, TaskConfig, task_manager


class TestTaskManager:
    """Pruebas del gestor de tareas en background"""

    def test_task_manager_imports(self):
        assert BackgroundTaskManager is not None
        assert TaskConfig is not None
        assert task_manager is not None

    def test_task_manager_submit(self):
        async def scenario():
            async def my_task():
                return "test result"
            info = await task_manager.submit(
                my_task,
                context="test",
                config=TaskConfig(max_retries=0)
            )
            assert info is not None
            assert hasattr(info, "task_id") or isinstance(info, str)

        asyncio.run(scenario())
