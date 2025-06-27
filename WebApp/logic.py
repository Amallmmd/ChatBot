from datetime import datetime
from typing import List, Dict, Tuple, Optional

REPORT_SEQUENCE = [
    "At Sea",
    "Arrival",
    "Arrival At Berth",
    "In Port",  # Can repeat any number of times between Arrival At Berth and Departure From Berth
    "Departure From Berth",
    "Departure"
]

# Helper to get the next valid report types
def get_next_valid_report_types(history):
    # Remove consecutive duplicates
    filtered = [history[0]] if history else []
    for r in history[1:]:
        if r != filtered[-1]:
            filtered.append(r)
    # Find last non-In Port report
    last = None
    for r in reversed(filtered):
        if r != "In Port":
            last = r
            break
    if last is None:
        return [REPORT_SEQUENCE[0]]
    idx = REPORT_SEQUENCE.index(last)
    if last == "Arrival At Berth":
        return ["Arrival At Berth", "In Port", "Departure From Berth"]
    if last == "Departure From Berth":
        return ["Departure From Berth", "In Port", "Departure"]
    if last == "In Port":
        return ["In Port", "Arrival At Berth", "Departure From Berth"]
    if last == "Arrival":
        return ["Arrival","Arrival At Berth"]
    if last == "At Sea":
        return ["At Sea","Arrival"]
    if last == "Departure":
        return []
    return [REPORT_SEQUENCE[idx+1]] if idx+1 < len(REPORT_SEQUENCE) else []

def check_report_sequence(vessel_history, new_report_type):
    history_types = [row['Report_Type'] for row in vessel_history]
    valid_next = get_next_valid_report_types(history_types)
    # In Port can repeat between Arrival At Berth and Departure From Berth
    if new_report_type == "In Port":
        if "Arrival At Berth" in history_types and ("Departure From Berth" not in history_types or history_types.index("Arrival At Berth") > history_types.index("Departure From Berth") ):
            return True, None
        else:
            return False, ("'In Port' is only allowed after 'Arrival At Berth' and before 'Departure From Berth'. "
                           "Please enter 'In Port' only between these two events.")
    if new_report_type in valid_next:
        return True, None
    # Format valid_next as a natural language list
    if len(valid_next) == 1:
        valid_str = valid_next[0]
    elif len(valid_next) == 2:
        valid_str = f"{valid_next[0]} or {valid_next[1]}"
    else:
        valid_str = ", ".join(valid_next[:-1]) + f", or {valid_next[-1]}"
    return False, (f"The next valid report type should be {valid_str}, but you entered '{new_report_type}'. "
                   f"Please check the sequence and try again.")

def check_laden_ballast_change(vessel_history, new_laden_ballast, new_report_type):
    # Only allow Laden/Ballast change after 'Arrival At Berth'
    if len(vessel_history) < 1:
        return True, None
    prev_status = vessel_history[-1]['Laden_Ballst']
    prev_report = vessel_history[-1]['Report_Type']
    if prev_status != new_laden_ballast:
        # Only allow change if previous report was 'Arrival At Berth' or later
        allowed = False
        for row in reversed(vessel_history):
            if row['Report_Type'] == 'Arrival At Berth':
                allowed = True
                break
            if row['Report_Type'] in ['Departure From Berth', 'Departure']:
                break
        if not allowed:
            return False, "Laden/Ballast status can only change after 'Arrival At Berth'."
    return True, None

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
