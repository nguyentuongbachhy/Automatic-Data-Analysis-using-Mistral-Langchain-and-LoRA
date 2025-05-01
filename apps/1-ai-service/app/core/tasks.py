import asyncio
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """Manager for background tasks"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = BackgroundTaskManager()
        return cls._instance
    
    def __init__(self):
        """Initialize task manager"""
        self.tasks = {}
        self.results = {}
        self.max_tasks = 10
        
    async def run_task(self, task_id: str, func: Callable, *args, **kwargs) -> None:
        """Run a task in the background and store its result"""
        try:
            result = await func(*args, **kwargs)
            
            self.results[task_id] = {
                "status": "completed",
                "result": result
            }
        except Exception as e:
            logger.error(f"Error in background task {task_id}: {str(e)}", exc_info=e)
            self.results[task_id] = {
                "status": "failed",
                "error": str(e)
            }
        finally:
            if task_id in self.tasks:
                del self.tasks[task_id]
    
    def submit_task(self, task_id: str, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Submit a task to be run in the background"""
        if len(self.tasks) >= self.max_tasks:
            return {
                "status": "rejected",
                "message": "Too many active tasks"
            }
            
        task = asyncio.create_task(self.run_task(task_id, func, *args, **kwargs))
        
        self.tasks[task_id] = task
        self.results[task_id] = {
            "status": "running"
        }
        
        return {
            "status": "submitted",
            "task_id": task_id
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task"""
        return self.results.get(task_id)
    
    def clear_completed_tasks(self) -> int:
        """Clear completed tasks from results"""
        completed_tasks = [
            task_id for task_id, status in self.results.items()
            if status["status"] in ["completed", "failed"]
        ]
        
        for task_id in completed_tasks:
            if task_id in self.results:
                del self.results[task_id]
                
        return len(completed_tasks)