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
    The latest date for this entry is {conversation_history[-1]['content'].split()[-1]}.

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

    Example JSON for proceeding:
    ```json
    {{
      "action": "proceed",
      "bot_response": "Understood. I will update the data with the new status. Is there anything else?"
    }}
    ```
    Example JSON for correcting to Laden:
    ```json
    {{
      "action": "correct",
      "corrected_status": "Laden",
      "bot_response": "Okay, I'll update the status to Laden. Confirming this change now."
    }}
    ```
    Example JSON for clarification:
    ```json
    {{
      "action": "clarify",
      "bot_response": "This flag means that Vessel {vessel_name} has been consistently {previous_status} in its recent reports, but your new entry indicates {new_status}. Are you sure about this change?"
    }}
    ```
    Example JSON for correcting but no status specified:
    ```json
    {{
      "action": "clarify",
      "bot_response": "Certainly, I can help you correct it. Do you want to change it to 'Laden' or 'Ballast'?"
    }}
    ```

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

def generate_initial_polite_message(vessel_name, prev_status, new_status, date_str, report_type, model):
    initial_message_prompt = f"""
        You are a helpful and polite assistant for a maritime data entry system. A user (Vessel Master) is trying to enter noon data.
        The vessel '{vessel_name}' has consistently been recorded as '{prev_status}' in its last 5 entries, but the new entry suggests it is now '{new_status}'.
        The latest entry date is {date_str}. The report type is '{report_type}'.
        Please craft a very polite, conversational, and concise initial message to the user, strictly limited to one or two sentences.
        Start with a soft apology like \"Hey Master, Sorry for the trouble,\" or similar.
        Clearly state the observed change in 'Laden/Ballst' status for the vessel on the given date and mention the report type.
        Then, mention that your analysis of previous entries shows the consistent '{prev_status}' status.
        Finally, ask if they would like to review this change.

        Example desired tone: "Hey Master, Sorry for the trouble, I noticed a change in the 'Laden/Ballast' status for 'Navig8 Gallantry' from 'Laden' to 'Ballast' on 2025-06-11. When I analyze report type entries, it is supposed to be 'Laden'. Would you like to review this change?"
        """
    try:
        initial_polite_message = model.generate_content(initial_message_prompt).text
    except Exception as e:
        initial_polite_message = (f"We noticed a potential change for **{vessel_name}**: "
                                  f"It was previously **{prev_status}** for the last few entries, "
                                  f"but the new data shows **{new_status}** (Report Type: {report_type}). "
                                  f"Is this change intentional, or would you like to correct the 'Laden/Ballast' status?")
    return initial_polite_message
