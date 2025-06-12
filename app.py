import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import google.generativeai as genai
import random
from dotenv import load_dotenv # Import load_dotenv
import json # Import json for parsing Gemini's structured output

# --- 0. Configure Gemini API ---
# Load environment variables from .env file
load_dotenv()

# Access the API key from environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    st.error("GOOGLE_API_KEY environment variable not set. Please ensure you have a .env file with GOOGLE_API_KEY='YOUR_API_KEY_HERE'.")
    st.stop() # Stop the app if API key is not found

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# --- 1. Dummy Data Generation ---
def generate_dummy_data():
    data = []
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=60)
    def random_date_in_range(start, end):
        delta = (end - start).days
        random_days = random.randint(0, delta)
        return start + timedelta(days=random_days)
    # Navig8 Messi: Full Laden
    for i in range(5):
        random_dt = random_date_in_range(start_date, end_date)
        data.append({
            'Vessel_name': 'Navig8 Messi',
            'Date': random_dt.strftime('%Y-%m-%d'),
            # 'Draft': round(10.0 + random.uniform(-0.5, 0.5), 2),
            'Laden/Ballst': 'Laden',
            # 'Power': random.randint(14000, 16000)
        })
    # Navig8 Guard: Full Ballast
    for i in range(5):
        random_dt = random_date_in_range(start_date, end_date)
        data.append({
            'Vessel_name': 'Navig8 Guard',
            'Date': random_dt.strftime('%Y-%m-%d'),
            # 'Draft': round(5.0 + random.uniform(-0.2, 0.2), 2),
            'Laden/Ballst': 'Ballast',
            # 'Power': random.randint(9000, 11000)
        })
    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df = df.sort_values(by=['Vessel_name', 'Date'], ascending=[True, False]).reset_index(drop=True)
    return df

# --- 2. Initialize Session State ---
if 'noon_data' not in st.session_state:
    st.session_state.noon_data = generate_dummy_data()
if 'contradiction_pending_confirmation' not in st.session_state:
    st.session_state.contradiction_pending_confirmation = False
if 'entry_to_confirm' not in st.session_state:
    st.session_state.entry_to_confirm = {}
if 'previous_vessel_status' not in st.session_state:
    st.session_state.previous_vessel_status = None
# The 'correcting_laden_ballast' state is no longer needed as correction happens via chat
# if 'correcting_laden_ballast' not in st.session_state:
#     st.session_state.correcting_laden_ballast = False
if 'contradiction_chat_history' not in st.session_state: # Initialize chat history
    st.session_state.contradiction_chat_history = []
if 'latest_added_vessel' not in st.session_state:
    st.session_state.latest_added_vessel = None

# --- 3. Helper Functions ---

def check_for_contradiction(vessel_name, new_laden_ballast, df, lookback_rows=5):
    """
    Checks the last 'lookback_rows' for a vessel's Laden/Ballast status.
    Flags a contradiction if all previous entries are one status and the new one is the opposite.
    """
    # Filter for the specific vessel and sort by time in descending order
    vessel_df = df[df['Vessel_name'] == vessel_name].sort_values(by='Date', ascending=False)

    if len(vessel_df) < lookback_rows:
        # Not enough historical data to make a strong determination
        return False, None

    # Get the Laden/Ballast status of the most recent entries
    recent_statuses = vessel_df['Laden/Ballst'].head(lookback_rows).unique()

    if len(recent_statuses) == 1: # All recent entries have the same status
        previous_status = recent_statuses[0]
        if previous_status != new_laden_ballast:
            return True, previous_status # Contradiction detected
    return False, None

def generate_chat_response(conversation_history, vessel_name, previous_status, new_status):
    """
    Uses Gemini API to generate a response during the contradiction chat,
    and attempts to interpret user intent for proceeding or correcting.
    Returns a dictionary with 'action', 'corrected_status' (if applicable), and 'bot_response'.
    """
    # Format conversation history for Gemini
    formatted_conversation = []
    for msg in conversation_history:
        if msg['role'] == 'user':
            formatted_conversation.append(f"User: {msg['content']}")
        else:
            formatted_conversation.append(f"Assistant: {msg['content']}")
    
    conversation_str = "\n".join(formatted_conversation)

    # IMPORTANT: Instruct Gemini to output JSON for reliable parsing of intent
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
        # Attempt to parse the JSON response
        response_text = response.text.strip()
        # Gemini sometimes adds markdown ```json ... ```, so we need to strip it
        if response_text.startswith("```json") and response_text.endswith("```"):
            response_text = response_text[7:-3].strip()
        
        parsed_response = json.loads(response_text)
        return parsed_response
    except json.JSONDecodeError as e:
        st.error(f"Error parsing Gemini's JSON response: {e}\nRaw response: {response.text}")
        return {
            "action": "clarify",
            "bot_response": "I'm sorry, I had trouble understanding that. Could you please rephrase or be more direct? For example, 'Yes, proceed' or 'Change to Laden'."
        }
    except Exception as e:
        st.error(f"Error generating chat response with Gemini: {e}")
        return {
            "action": "clarify",
            "bot_response": "I'm sorry, I couldn't process that. Please try again or make your decision."
        }


def add_entry(new_entry_data):
    """Appends a new entry to the DataFrame and sorts it."""
    new_df_row = pd.DataFrame([new_entry_data])
    new_df_row['Date'] = pd.to_datetime(new_df_row['Date']).dt.date
    st.session_state.noon_data = pd.concat([st.session_state.noon_data, new_df_row], ignore_index=True)
    # Re-sort the entire DataFrame after adding a new row
    st.session_state.noon_data = st.session_state.noon_data.sort_values(by=['Vessel_name', 'Date'], ascending=[True, False]).reset_index(drop=True)
    st.success(f"New entry for {new_entry_data['Vessel_name']} added successfully!")
    # Clear any pending states and chat history
    st.session_state.contradiction_pending_confirmation = False
    st.session_state.entry_to_confirm = {}
    st.session_state.previous_vessel_status = None
    st.session_state.contradiction_chat_history = [] # Clear chat history on successful action
    st.session_state.latest_added_vessel = new_entry_data['Vessel_name']

# --- 4. Streamlit UI ---
st.set_page_config(layout="wide", page_title="Noon Data Chatbot")

# Center the title and subtitle using HTML and Streamlit's markdown with unsafe_allow_html, in a centered column
col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    st.markdown("""
        <div style='text-align: center;'>
            <h1>🚢 Noon Data Entry Chatbot</h1>
            <p>Enter new noon reports and get intelligent feedback on potential discrepancies.</p>
        </div>
        """, unsafe_allow_html=True)
    st.header("Add New Noon Entry")

# Input form for new data (centered, using half the width)
col_left, col_form, col_right = st.columns([1, 2, 1])
with col_form:
    with st.expander("Click to add a new entry", expanded=True):
        with st.form("new_entry_form", clear_on_submit=False):
            # Get unique vessel names from current data, plus "New Vessel" option
            existing_vessels = st.session_state.noon_data['Vessel_name'].unique().tolist()
            
            # Determine initial index for selectbox
            initial_vessel_index = 0
            if "Navig8 Messi" in existing_vessels: # Try to default to Navig8 Messi if it exists
                initial_vessel_index = existing_vessels.index("Navig8 Messi")
            
            vessel_name_selection = st.selectbox(
                "Vessel Name", 
                options=existing_vessels + ["New Vessel"], 
                index=initial_vessel_index,
                key="vessel_name_select"
            )
            
            vessel_name_input = vessel_name_selection
            if vessel_name_selection == "New Vessel":
                vessel_name_input = st.text_input("Enter New Vessel Name", key="new_vessel_name_input")

            # Only date input
            date_str = st.date_input("Date", value=datetime.now().date(), key="date_input")
            # draft = st.number_input("Draft (meters)", min_value=0.0, max_value=20.0, value=8.5, step=0.1)
            laden_ballast = st.selectbox("Laden/Ballast", options=['Laden', 'Ballast'])
            # power = st.number_input("Power (kW)", min_value=0, max_value=30000, value=12000, step=100)

            submitted = st.form_submit_button("Add Entry")

            if submitted:
                # Check if a new vessel name was entered and is not empty
                if vessel_name_selection == "New Vessel" and not vessel_name_input.strip():
                    st.error("Please enter a name for the new vessel.")
                    st.stop()

                try:
                    new_entry = {
                        'Vessel_name': vessel_name_input.strip(),
                        'Date': date_str,
                        # 'Draft': draft,
                        'Laden/Ballst': laden_ballast,
                        # 'Power': power
                    }

                    # Check for contradiction only if not already in a pending confirmation state
                    if not st.session_state.contradiction_pending_confirmation: # Removed correcting_laden_ballast check
                        # Only check for contradiction if the vessel already exists in the data
                        if new_entry['Vessel_name'] in existing_vessels:
                            is_contradiction, prev_status = check_for_contradiction(
                                new_entry['Vessel_name'],
                                new_entry['Laden/Ballst'],
                                st.session_state.noon_data
                            )

                            if is_contradiction:
                                st.session_state.contradiction_pending_confirmation = True
                                st.session_state.entry_to_confirm = new_entry
                                st.session_state.previous_vessel_status = prev_status
                                
                                # Generate initial polite message only if chat history is empty
                                if not st.session_state.contradiction_chat_history:
                                    # For the initial message, we just want the polite text, not JSON parsing
                                    initial_message_prompt = f"""
                                        You are a helpful and polite assistant for a maritime data entry system. A user (Vessel Master) is trying to enter noon data.
                                        The vessel '{new_entry['Vessel_name']}' has consistently been recorded as '{prev_status}' in its last 5 entries, but the new entry suggests it is now '{new_entry['Laden/Ballst']}'.
                                        The latest entry date is {date_str}.

                                        Please craft a very polite, conversational, and concise initial message to the user, strictly limited to one or two sentences.
                                        Start with a soft apology like "Hey Master, Sorry for the trouble," or similar.
                                        Clearly state the observed change in 'Laden/Ballst' status for the vessel on the given date.
                                        Then, mention that your analysis of previous entries shows the consistent '{prev_status}' status.
                                        Finally, ask if they would like to review this change.

                                        Example desired tone: "Hey Master, Sorry for the trouble, I noticed a change in the 'Laden/Ballast' status for 'Navig8 Gallantry' from 'Laden' to 'Ballast' on 2025-06-11. When I analyze previous entries, it shows 'Laden'. Would you like to review this change?"
                                        """
                                    try:
                                        initial_polite_message = model.generate_content(initial_message_prompt).text
                                    except Exception as e:
                                        initial_polite_message = (f"We noticed a potential change for **{new_entry['Vessel_name']}**: "
                                                                  f"It was previously **{prev_status}** for the last few entries, "
                                                                  f"but the new data shows **{new_entry['Laden/Ballst']}**. "
                                                                  f"Is this change intentional, or would you like to correct the 'Laden/Ballast' status?")
                                    
                                    st.session_state.contradiction_chat_history.append({
                                        'role': 'assistant',
                                        'content': initial_polite_message
                                    })
                                st.info("A potential contradiction was detected. Please use the chat below to confirm or correct.")
                            else:
                                add_entry(new_entry)
                        else:
                            # If it's a new vessel, no contradiction check is needed
                            add_entry(new_entry)
                    else:
                        st.warning("Please resolve the pending contradiction first using the chat interface.")

                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")

# --- Contradiction Resolution UI (Chat-driven) ---
col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    if st.session_state.contradiction_pending_confirmation:
        st.subheader("Action Required: Contradiction Detected")
        # Only show the chatbox at the bottom (do not display previous chat history above)
        # Chat input for user interaction (locked at the bottom)
        chat_placeholder = st.empty()
        def render_chat():
            for msg in st.session_state.contradiction_chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
        render_chat()
        if prompt := st.chat_input("Type 'proceed' to confirm, or 'change to Laden/Ballast' to correct...", key="contradiction_chat_input"):
            st.session_state.contradiction_chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    latest_date = st.session_state.entry_to_confirm.get('Date', datetime.now().date())
                    gemini_response = generate_chat_response(
                        st.session_state.contradiction_chat_history,
                        st.session_state.entry_to_confirm.get('Vessel_name', 'the vessel'),
                        st.session_state.previous_vessel_status,
                        st.session_state.entry_to_confirm.get('Laden/Ballst', ''),
                    )
                st.write(gemini_response.get('bot_response', ''))
                st.session_state.contradiction_chat_history.append({"role": "assistant", "content": gemini_response.get('bot_response', '')})
                action = gemini_response.get('action')
                if action == "proceed":
                    add_entry(st.session_state.entry_to_confirm)
                    st.session_state.contradiction_pending_confirmation = False
                    st.session_state.show_contradiction_chat = False
                    st.success("Data updated as requested!")
                elif action == "correct":
                    corrected_status = gemini_response.get('corrected_status')
                    if corrected_status in ['Laden', 'Ballast']:
                        st.session_state.entry_to_confirm['Laden/Ballst'] = corrected_status
                        add_entry(st.session_state.entry_to_confirm)
                        st.session_state.contradiction_pending_confirmation = False
                        st.session_state.show_contradiction_chat = False
                        st.success(f"Data updated to {corrected_status} as requested!")
                    else:
                        st.warning("Please specify 'Laden' or 'Ballast' to correct the status.")

# Display current data with a button to show/hide
col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    if 'show_noon_data' not in st.session_state:
        st.session_state.show_noon_data = False
    if st.button("Show/Hide Current Noon Data", key="show_noon_data_btn"):
        st.session_state.show_noon_data = not st.session_state.show_noon_data
        st.session_state.contradiction_pending_confirmation = False
        st.session_state.contradiction_chat_history = []
    if st.session_state.show_noon_data:
        vessel = st.session_state.get('latest_added_vessel', None)
        if vessel:
            vessel_df = st.session_state.noon_data[st.session_state.noon_data['Vessel_name'] == vessel].copy()
            vessel_df = vessel_df.sort_values(by='Date', ascending=False)
            st.header(f"Current Noon Data for {vessel}")
            st.dataframe(vessel_df, use_container_width=True)
        else:
            st.info("No vessel data to display yet.")