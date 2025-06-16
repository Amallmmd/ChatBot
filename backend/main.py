from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from backend.models import NoonEntry, ContradictionCheckRequest, ContradictionCheckResponse, ChatRequest, ChatResponse, AddEntryRequest, NoonDataResponse
from backend.storage import storage
from backend.logic import check_for_contradiction
from backend.gemini_api import generate_chat_response
from typing import List

app = FastAPI()

app.mount("/static", StaticFiles(directory="backend/static"), name="static")
templates = Jinja2Templates(directory="backend/templates")

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
    entry = req.entry.dict()
    storage.add_entry(entry)
    return {"success": True}

@app.post("/check_contradiction", response_model=ContradictionCheckResponse)
def check_contradiction(req: ContradictionCheckRequest):
    data = storage.get_data()
    is_contradiction, previous_status, reason = check_for_contradiction(
        req.vessel_name, req.new_laden_ballast, req.new_report_type, data
    )
    return ContradictionCheckResponse(
        is_contradiction=is_contradiction,
        previous_status=previous_status,
        reason=reason
    )

@app.post("/chat_response", response_model=ChatResponse)
def chat_response(req: ChatRequest):
    result = generate_chat_response(
        req.conversation_history,
        req.vessel_name,
        req.previous_status,
        req.new_status
    )
    return ChatResponse(**result)

@app.get("/get_noon_data", response_model=NoonDataResponse)
def get_noon_data():
    data = storage.get_data()
    return NoonDataResponse(data=data)
