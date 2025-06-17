import threading
from typing import List, Dict
from datetime import date, datetime, timedelta
import random

# In-memory storage for demo (thread-safe)
class DataStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = []
        self._initialized = False

    def generate_dummy_data(self):
        data = []
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=60)
        def random_date_in_range(start, end):
            delta = (end - start).days
            random_days = random.randint(0, delta)
            return start + timedelta(days=random_days)
        report_types = ['At Sea', 'Arrival', 'Departure', 'Arrival At Berth', 'Departure From Berth']
        for i in range(5):
            random_dt = random_date_in_range(start_date, end_date)
            data.append({
                'Vessel_name': 'Navig8 Messi',
                'Date': random_dt.strftime('%Y-%m-%d'),
                'Laden_Ballst': 'Laden',
                'Report_Type': random.choice(report_types)
            })
        for i in range(5):
            random_dt = random_date_in_range(start_date, end_date)
            data.append({
                'Vessel_name': 'Navig8 Guard',
                'Date': random_dt.strftime('%Y-%m-%d'),
                'Laden_Ballst': 'Ballast',
                'Report_Type': random.choice(report_types)
            })
        return data

    def initialize(self):
        with self._lock:
            if not self._initialized:
                self._data = self.generate_dummy_data()
                self._initialized = True

    def add_entry(self, entry: Dict):
        with self._lock:
            self._data.append(entry)
            vessel_name = entry['Vessel_name']
            # Ensure all dates are datetime.date for sorting
            for row in self._data:
                if row['Vessel_name'] == vessel_name:
                    if isinstance(row['Date'], str):
                        try:
                            row['Date'] = datetime.strptime(row['Date'], "%Y-%m-%d").date()
                        except Exception:
                            pass
            vessel_entries = [row for row in self._data if row['Vessel_name'] == vessel_name]
            vessel_entries.sort(key=lambda x: x['Date'], reverse=True)
            self._data = [row for row in self._data if row['Vessel_name'] != vessel_name]
            self._data.extend(vessel_entries)

    def get_data(self) -> List[Dict]:
        with self._lock:
            return list(self._data)

    def clear(self):
        with self._lock:
            self._data = []
            self._initialized = False

storage = DataStorage()
storage.initialize()
