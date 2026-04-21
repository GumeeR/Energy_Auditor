from datetime import datetime
from typing import Dict, Any, Optional
import threading

class JobsStore:

    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str, request_data: Dict[str, Any]) -> None:
        with self._lock:
            self._data[job_id] = {
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "request": request_data,
                "result": None,
            }

    def update_status(self, job_id: str, status: str) -> None:
        with self._lock:
            if job_id in self._data:
                self._data[job_id]["status"] = status

    def set_result(self, job_id: str, result: Dict[str, Any], status: str = "done") -> None:
        with self._lock:
            if job_id in self._data:
                self._data[job_id]["status"] = status
                self._data[job_id]["result"] = result

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._data.get(job_id)

    def exists(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._data

store = JobsStore()