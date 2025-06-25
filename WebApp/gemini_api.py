import os
from dotenv import load_dotenv
import google.generativeai as genai
import json

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set in .env file.")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

def generate_chat_response(conversation_history, vessel_name, previous_status, new_status, new_report_type, seq_reason=None, laden_reason=None):
    formatted_conversation = []
    for msg in conversation_history:
        if msg['role'] == 'user':
            formatted_conversation.append(f"User: {msg['content']}")
        else:
            formatted_conversation.append(f"Assistant: {msg['content']}")
    conversation_str = "\n".join(formatted_conversation)
    prompt = f"""
    You are a helpful assistant for a maritime data entry system. The user is currently entering noon data for vessel '{vessel_name}'.
    A potential contradiction or rule violation was flagged: the vessel was consistently '{previous_status}' in its last entries, but the new entry suggests '{new_status}' (Report Type: '{new_report_type}').
    The following is the ongoing conversation between the user and you (the assistant) regarding this specific contradiction or rule violation.
    If there is a report type sequence or status change rule violation, explain it clearly and politely in your response.
    Your goal is to:
    1.  Maintain context of the vessel and the contradiction or rule violation.
    2.  Answer user questions naturally, concisely, and helpfully.
    3.  If the user asks for clarification, provide details about the contradiction or rule violation and why it was flagged.
    4.  If the user indicates they want to proceed with the new '{new_status}' status or a new report type, set `action` to "proceed".
    4a. If the user indicates they want to proceed with the new '{new_report_type}' report type or a new status, set `action` to "proceed".
    5.  If the user indicates they want to correct the status, set `action` to "correct_status" and identify the `corrected_status` as either "Laden" or "Ballast". If the user says "correct it" but doesn't specify which, ask them to clarify.
    5a.  If the user indicates they want to correct the report type, set `action` to "correct_report_type" and identify the `corrected_report_type` (e.g., "Arrival", "Departure").
    6.  For any other questions or clarifications, set `action` to "clarify".
    Respond ONLY with a JSON object. The JSON object must have the following keys:
    - `action`: "proceed" | "correct_status" | "correct_report_type" | "clarify"
    - `corrected_status`: "Laden" | "Ballast" (only if `action` is "correct_status" and status is specified)
    - `corrected_report_type`: "At Sea" | "Arrival" | "In Port" | "Departure" | "Arrival at Berth" | "Departure from Berth" (only if `action` is "correct_report_type" and report type is specified)
    - `bot_response`: A natural language response to the user.
    """
    if seq_reason:
        prompt += f"\nNote: {seq_reason}"
    if laden_reason:
        prompt += f"\nNote: {laden_reason}"
    prompt += f"\n{conversation_str}\nAssistant:"
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        if response_text.startswith("```json") and response_text.endswith("```"):
            response_text = response_text[7:-3].strip()
        parsed_response = json.loads(response_text)
        return parsed_response
    except Exception as e:
        return {
            "action": "clarify",
            "bot_response": f"I'm sorry, I couldn't process that. Please try again or make your decision. (Error: {e})"
        }

def generate_initial_polite_message(vessel_name, prev_status, new_status, date_str, report_type, model, seq_reason=None, laden_reason=None):
    initial_message_prompt = f"""
        You are a helpful and polite assistant for a maritime data entry system. A user (Vessel Master) is trying to enter noon data.
        The vessel '{vessel_name}' has consistently been recorded as '{prev_status}' in its last 5 entries, but the new entry suggests it is now '{new_status}'.
        The latest entry date is {date_str}. The report type is '{report_type}'.
        Please craft a very polite, conversational, and concise initial message to the user, strictly limited to one or two sentences.
        Start with a soft apology like \"Hey Master, Sorry for the trouble,\" or similar.
        Clearly state the observed change in 'Laden/Ballst' status for the vessel '{vessel_name}' on the given date and mention the report type.
        Then, mention that your analysis of previous entries shows the consistent '{prev_status}' status.
        If there is a report type sequence or status change rule violation, explain it clearly and politely."
    """
    if seq_reason:
        initial_message_prompt += f"\nNote: {seq_reason}"
    if laden_reason:
        initial_message_prompt += f"\nNote: {laden_reason}"
    initial_message_prompt += "\nFinally, ask if they would like to review or correct this change."
    initial_message_prompt += "\n\nExample desired tone: 'Hey Master, Sorry for the trouble, I noticed a change in the 'Laden/Ballast' status for '{vessel_name}' from '{prev_status}' to '{new_status}' on {date_str}. When I analyze report type entries, it is supposed to be '{prev_status}'. Would you like to review this change?'"
    try:
        initial_polite_message = model.generate_content(initial_message_prompt).text
    except Exception as e:
        initial_polite_message = (f"We noticed a potential change for **{vessel_name}**: "
                                  f"It was previously **{prev_status}** for the last few entries, "
                                  f"but the new data shows **{new_status}** (Report Type: {report_type}). "
                                  f"Is this change intentional, or would you like to correct the 'Laden/Ballast' status? "
                                  f"{seq_reason or ''} {laden_reason or ''}")
    return initial_polite_message
