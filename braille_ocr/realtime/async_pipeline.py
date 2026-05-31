"""
async_pipeline.py
-----------------
Production-ready asynchronous pipeline for Braille OCR.
Uses concurrent.futures to offload heavy OCR and CNN inference tasks from the main thread.
"""

import concurrent.futures
from typing import Callable, Any
import time

class AsyncOCRPipeline:
    def __init__(self, max_workers: int = 4):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.futures = {}

    def submit_task(self, task_id: str, func: Callable, *args, **kwargs):
        """
        Submits an OCR or Inference task to the background pool.
        """
        future = self.executor.submit(func, *args, **kwargs)
        self.futures[task_id] = {
            "future": future,
            "submitted_at": time.time(),
            "status": "pending"
        }
        return task_id

    def get_result(self, task_id: str, timeout: float = None) -> Any:
        """
        Retrieves the result of a background task. 
        Returns None if not ready or on error.
        """
        if task_id not in self.futures:
            return None
            
        task = self.futures[task_id]
        future = task["future"]
        
        if future.done():
            try:
                result = future.result(timeout=timeout)
                task["status"] = "completed"
                return result
            except Exception as e:
                task["status"] = f"error: {str(e)}"
                return None
        return None

    def is_done(self, task_id: str) -> bool:
        if task_id not in self.futures:
            return False
        return self.futures[task_id]["future"].done()

    def shutdown(self):
        self.executor.shutdown(wait=False)

# Global singleton for easy import
async_ocr = AsyncOCRPipeline()
