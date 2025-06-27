from pydantic import BaseModel
from typing import Optional
from datetime import date

class NoonEntry(BaseModel):
    Vessel_name: str
    Date: date
    Laden_Ballst: str
    Report_Type: str

class ContradictionCheckRequest(BaseModel):
    vessel_name: str
    new_laden_ballast: str
    new_report_type: str

class ContradictionCheckResponse(BaseModel):
    is_contradiction: bool
    previous_status: Optional[str]
    reason: Optional[str]

class ChatRequest(BaseModel):
    conversation_history: list
    vessel_name: str
    previous_status: Optional[str]
    new_status: str
    new_report_type: str
    # date: str  # <-- Add this field

class ChatResponse(BaseModel):
    action: str
    corrected_status: Optional[str] = None
    bot_response: str

class AddEntryRequest(BaseModel):
    entry: NoonEntry

class NoonDataResponse(BaseModel):
    data: list
