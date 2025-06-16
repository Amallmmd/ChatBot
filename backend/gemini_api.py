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

def generate_chat_response(conversation_history, vessel_name, previous_status, new_status):
    formatted_conversation = []
    for msg in conversation_history:
        if msg['role'] == 'user':
            formatted_conversation.append(f"User: {msg['content']}")
        else:
            formatted_conversation.append(f"Assistant: {msg['content']}")
    conversation_str = "\n".join(formatted_conversation)
    prompt = f"""
    You are a helpful assistant for a maritime data entry system. The user is currently entering noon data for vessel '{vessel_name}'.
    A potential contradiction was flagged: the vessel was consistently '{previous_status}' in its last entries, but the new entry suggests '{new_status}'.
    The following is the ongoing conversation between the user and you (the assistant) regarding this specific contradiction.
    Your goal is to:
    1.  Maintain context of the vessel and the contradiction.
    2.  Answer user questions naturally, concisely, and helpfully.
    3.  If the user asks for clarification, provide details about the contradiction and why it was flagged.
    4.  If the user indicates they want to proceed with the new '{new_status}' status, set `action` to "proceed".
    5.  If the user indicates they want to correct the status, set `action` to "correct" and identify the `corrected_status` as either "Laden" or "Ballast". If the user says "correct it" but doesn't specify which, ask them to clarify.
    6.  For any other questions or clarifications, set `action` to "clarify".
    Respond ONLY with a JSON object. The JSON object must have the following keys:
    - `action`: "proceed" | "correct" | "clarify"
    - `corrected_status`: "Laden" | "Ballast" (only if `action` is "correct" and status is specified)
    - `bot_response`: A natural language response to the user.
    {conversation_str}
    Assistant:"""
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
