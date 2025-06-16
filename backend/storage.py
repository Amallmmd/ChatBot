import threading
from typing import List, Dict
from datetime import date

# In-memory storage for demo (thread-safe)
class DataStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = []

    def add_entry(self, entry: Dict):
        with self._lock:
            self._data.append(entry)

    def get_data(self) -> List[Dict]:
        with self._lock:
            return list(self._data)

    def clear(self):
        with self._lock:
            self._data = []

storage = DataStorage()
