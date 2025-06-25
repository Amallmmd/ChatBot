from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from WebApp.models import NoonEntry, ContradictionCheckRequest, ContradictionCheckResponse, ChatRequest, ChatResponse, AddEntryRequest, NoonDataResponse
from WebApp.storage import storage
from WebApp.logic import check_for_contradiction, check_report_sequence, check_laden_ballast_change
from WebApp.gemini_api import generate_chat_response, generate_initial_polite_message, model
from typing import List

app = FastAPI()

app.mount("/static", StaticFiles(directory="WebApp/static"), name="static")
templates = Jinja2Templates(directory="WebApp/templates")

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/add_entry")
def add_entry(req: AddEntryRequest):
    entry = req.entry.model_dump()
    storage.add_entry(entry)
    return {"success": True}

def get_last_known_status_and_report(vessel_history):
    if not vessel_history:
        return None, None
    last_entry = vessel_history[-1]
    prev_status = last_entry.get('Laden_Ballst') or last_entry.get('Laden/Ballst')
    prev_report = last_entry.get('Report_Type')
    return prev_status, prev_report

@app.post("/check_contradiction", response_model=ContradictionCheckResponse)
def check_contradiction(req: ContradictionCheckRequest):
    data = storage.get_data()
    vessel_history = [row for row in data if row['Vessel_name'] == req.vessel_name]
    prev_status, prev_report = get_last_known_status_and_report(vessel_history)
    is_seq_valid, seq_reason = check_report_sequence(vessel_history, req.new_report_type)
    is_laden_valid, laden_reason = check_laden_ballast_change(vessel_history, req.new_laden_ballast, req.new_report_type)
    is_contradiction, _, reason = check_for_contradiction(
        req.vessel_name, req.new_laden_ballast, req.new_report_type, data
    )
    initial_message = None
    if not is_seq_valid:
        reason = seq_reason
        is_contradiction = True
    elif not is_laden_valid:
        reason = laden_reason
        is_contradiction = True
    if is_contradiction:
        # Generate initial polite message for contradiction
        initial_message = generate_initial_polite_message(
            vessel_name=req.vessel_name,
            prev_status=prev_status or 'Unknown',
            new_status=req.new_laden_ballast or 'Unknown',
            date_str=str(data[0]['Date']) if data else '',
            report_type=req.new_report_type or 'Unknown',
            model=model,
            seq_reason=seq_reason if not is_seq_valid else None,
            laden_reason=laden_reason if not is_laden_valid else None
        )
    return ContradictionCheckResponse(
        is_contradiction=is_contradiction,
        previous_status=prev_status,
        reason=initial_message if initial_message else reason
    )

@app.post("/chat_response", response_model=ChatResponse)
def chat_response(req: ChatRequest):
    result = generate_chat_response(
        req.conversation_history,
        req.vessel_name,
        req.previous_status,
        req.new_status,
        req.new_report_type,
    )
    return ChatResponse(**result)

@app.get("/get_noon_data", response_model=NoonDataResponse)
def get_noon_data():
    data = storage.get_data()
    return NoonDataResponse(data=data)
