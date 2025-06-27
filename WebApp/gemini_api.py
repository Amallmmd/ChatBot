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
    5.  If the user indicates they want to correct the status, set `action` to "correct_status" and identify the `corrected_status` as either "Laden" or "Ballast". If the user says "correct it" but doesn't specify which, ask them to clarify.
    6.  For any other questions or clarifications, set `action` to "clarify".
    Respond ONLY with a JSON object. The JSON object must have the following keys:
    - `action`: "proceed" | "correct_status" | "correct_report_type" | "clarify"
    - `corrected_status`: "Laden" | "Ballast" (only if `action` is "correct_status" and status is specified)
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
    if seq_reason:
        # Report type issue: Only mention report type, sequence, and allowed types. No status, no correction question.
        initial_message_prompt = f"""
        You are a helpful and polite assistant for a maritime data entry system. A user (Vessel Master) is entering data for vessel '{vessel_name}' for the date {date_str}.
        A report type sequence issue was detected.
        
        Please craft a concise, natural, and clear message to the user explaining the specific report type issue. Do NOT mention Laden/Ballast status or ask for further corrections.
        
        Start with one clear sentence identifying the issue.
        Use bullet points to highlight what's wrong.
        Specify which is the aloowed sequence of report type by specifying {seq_reason}.
        Do not ask any follow-up questions or offer corrections.
        Do not start with phrases like "Okay, here's the message tailored to the user's specific scenario:".
        
        Example desired tone:
        "Hey Master, I've noticed an issue with the report type you've entered for {vessel_name} on {date_str}.
        - The report type you entered is '{report_type}'.
        - {seq_reason}"
        """
    elif laden_reason:
        # Laden/Ballast contradiction: Use the existing conversational prompt and ask for correction.
        initial_message_prompt = f"""
        You are a helpful and polite assistant for a maritime data entry system. A user (Vessel Master) is trying to enter noon data.
        The vessel '{vessel_name}' has consistently been recorded as '{prev_status}' in its last entries, but the new entry suggests it is now '{new_status}'.
        The latest entry date is {date_str}.
        Please craft a very polite, conversational, and concise initial message to the user, strictly limited to one or two sentences.
        Start with a soft apology like \"Hey Master,\" or similar.
        Clearly state the observed change in 'Laden/Ballst' status for the vessel '{vessel_name}' on the given date and mention the report type.
        Then, mention that your analysis of previous entries shows the consistent '{prev_status}' status.
        If there is a report type sequence or status change rule violation, explain it clearly and politely."
        """
        initial_message_prompt += f"\nNote: {laden_reason}"
        initial_message_prompt += "\nFinally, ask if they would like to review or correct this change status. Just need to raise the flag if the contradiction happens for report type."
        initial_message_prompt += f"\n\nExample desired tone: 'Hey Master, I noticed a change in the 'Laden/Ballast' status for '{vessel_name}' from '{prev_status}' to '{new_status}' on {date_str}. When I analyze report type entries, it is supposed to be '{prev_status}'. Would you like to review this change?'"
    else:
        # Fallback for generic or unexpected cases
        return (f"We noticed a potential issue for **{vessel_name}** on {date_str}. "
                f"The new entry is **{new_status}** with report type **{report_type}**, "
                f"while previous entries were **{prev_status}**. Please review this entry.")

    try:
        initial_polite_message = model.generate_content(initial_message_prompt).text
    except Exception as e:
        if seq_reason:
            initial_polite_message = (f"There is a report type issue for **{vessel_name}** on {date_str}.\n"
                                      f"- You entered: **{report_type}**.\n"
                                      f"- {seq_reason}\n")
        elif laden_reason:
            initial_polite_message = (f"There is a status change for **{vessel_name}** on {date_str}.\n"
                                      f"- New status: **{new_status}**\n"
                                      f"- Previous status: **{prev_status}**\n"
                                      f"Is this change correct?")
        else:
            initial_polite_message = f"An issue was detected with the entry for {vessel_name}. Please review."

    return initial_polite_message.strip()
