from datetime import datetime
from typing import List, Dict, Tuple, Optional

def check_for_contradiction(vessel_name: str, new_laden_ballast: str, new_report_type: str, data: List[Dict], lookback_rows: int = 5) -> Tuple[bool, Optional[str], Optional[str]]:
    vessel_df = [row for row in data if row['Vessel_name'] == vessel_name]
    vessel_df = sorted(vessel_df, key=lambda x: x['Date'], reverse=False)
    if len(vessel_df) < lookback_rows:
        return False, None, None
    recent_statuses = list({row['Laden_Ballst'] for row in vessel_df[:lookback_rows]})
    previous_status = recent_statuses[0] if len(recent_statuses) == 1 else None
    allowed_change_types = ['Departure', 'Departure From Berth']
    if new_report_type in allowed_change_types:
        return False, None, None
    if previous_status and previous_status != new_laden_ballast:
        return True, previous_status, f"Status changed from {previous_status} to {new_laden_ballast} without a typical event (Report Type: {new_report_type})"
    return False, None, None
