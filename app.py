import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import google.generativeai as genai
import random
from dotenv import load_dotenv # Import load_dotenv

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
    
    # Define a date range for random dates (e.g., last 60 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    def random_date_in_range(start, end):
        delta = end - start
        random_seconds = random.randint(0, int(delta.total_seconds()))
        return start + timedelta(seconds=random_seconds)

    # Vessel A: Full Laden
    for i in range(5):
        random_dt = random_date_in_range(start_date, end_date)
        data.append({
            'Vessel_name': 'Vessel A',
            'Time': random_dt.strftime('%Y-%m-%d %H:%M'),
            'Draft': round(10.0 + random.uniform(-0.5, 0.5), 2), # Random draft around 10.0
            'Laden/Ballst': 'Laden',
            'Power': random.randint(14000, 16000)
        })
    # Vessel B: Full Ballast
    for i in range(5):
        random_dt = random_date_in_range(start_date, end_date)
        data.append({
            'Vessel_name': 'Vessel B',
            'Time': random_dt.strftime('%Y-%m-%d %H:%M'),
            'Draft': round(5.0 + random.uniform(-0.2, 0.2), 2), # Random draft around 5.0
            'Laden/Ballst': 'Ballast',
            'Power': random.randint(9000, 11000)
        })
    
    df = pd.DataFrame(data)
    df['Time'] = pd.to_datetime(df['Time']) # Ensure Time is datetime object
    # Sort by vessel and then by time to ensure contradiction check works correctly
    df = df.sort_values(by=['Vessel_name', 'Time'], ascending=[True, False]).reset_index(drop=True)
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
if 'correcting_laden_ballast' not in st.session_state:
    st.session_state.correcting_laden_ballast = False

# --- 3. Helper Functions ---

def check_for_contradiction(vessel_name, new_laden_ballast, df, lookback_rows=5):
    """
    Checks the last 'lookback_rows' for a vessel's Laden/Ballast status.
    Flags a contradiction if all previous entries are one status and the new one is the opposite.
    """
    # Filter for the specific vessel and sort by time in descending order
    vessel_df = df[df['Vessel_name'] == vessel_name].sort_values(by='Time', ascending=False)

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

def generate_polite_message(vessel_name, previous_status, new_status):
    """Uses Gemini API to generate a polite message for contradiction."""
    prompt = f"""
    You are a helpful assistant for a maritime data entry system. A user is trying to enter noon data for a vessel.
    The vessel '{vessel_name}' has consistently been recorded as '{previous_status}' in its last 5 entries, but the new entry suggests it is now '{new_status}'.

    Please craft a polite and clear message to the user, explaining this potential discrepancy and asking if they wish to proceed with this change or if they would like to correct the 'Laden/Ballst' status. Emphasize that this is just a flag for review.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating message with Gemini: {e}")
        return (f"We noticed a potential change for **{vessel_name}**: "
                f"It was previously **{previous_status}** for the last few entries, "
                f"but the new data shows **{new_status}**. "
                f"Is this change intentional, or would you like to correct the 'Laden/Ballst' status?")

def add_entry(new_entry_data):
    """Appends a new entry to the DataFrame and sorts it."""
    new_df_row = pd.DataFrame([new_entry_data])
    new_df_row['Time'] = pd.to_datetime(new_df_row['Time']) # Ensure Time is datetime object
    st.session_state.noon_data = pd.concat([st.session_state.noon_data, new_df_row], ignore_index=True)
    # Re-sort the entire DataFrame after adding a new row
    st.session_state.noon_data = st.session_state.noon_data.sort_values(by=['Vessel_name', 'Time'], ascending=[True, False]).reset_index(drop=True)
    st.success(f"New entry for {new_entry_data['Vessel_name']} added successfully!")
    # Clear any pending states
    st.session_state.contradiction_pending_confirmation = False
    st.session_state.entry_to_confirm = {}
    st.session_state.previous_vessel_status = None
    st.session_state.correcting_laden_ballast = False


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
            if "Vessel A" in existing_vessels: # Try to default to Vessel A if it exists
                initial_vessel_index = existing_vessels.index("Vessel A")
            
            vessel_name_selection = st.selectbox(
                "Vessel Name", 
                options=existing_vessels + ["New Vessel"], 
                index=initial_vessel_index,
                key="vessel_name_select"
            )
            
            vessel_name_input = vessel_name_selection
            if vessel_name_selection == "New Vessel":
                vessel_name_input = st.text_input("Enter New Vessel Name", key="new_vessel_name_input")

            time_str = st.text_input("Time (YYYY-MM-DD HH:MM)", value=datetime.now().strftime('%Y-%m-%d %H:%M'))
            draft = st.number_input("Draft (meters)", min_value=0.0, max_value=20.0, value=8.5, step=0.1)
            laden_ballast = st.selectbox("Laden/Ballast", options=['Laden', 'Ballast'])
            power = st.number_input("Power (kW)", min_value=0, max_value=30000, value=12000, step=100)

            submitted = st.form_submit_button("Add Entry")

            if submitted:
                # Check if a new vessel name was entered and is not empty
                if vessel_name_selection == "New Vessel" and not vessel_name_input.strip():
                    st.error("Please enter a name for the new vessel.")
                    st.stop()

                try:
                    # Validate Time format
                    datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                    new_entry = {
                        'Vessel_name': vessel_name_input.strip(), # Use the input value, strip whitespace
                        'Time': time_str,
                        'Draft': draft,
                        'Laden/Ballst': laden_ballast,
                        'Power': power
                    }

                    # Check for contradiction only if not already in a pending confirmation state
                    if not st.session_state.contradiction_pending_confirmation and not st.session_state.correcting_laden_ballast:
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
                                st.warning(generate_polite_message(
                                    new_entry['Vessel_name'],
                                    prev_status,
                                    new_entry['Laden/Ballst']
                                ))
                                st.info("Please confirm your decision below.")
                            else:
                                add_entry(new_entry)
                        else:
                            # If it's a new vessel, no contradiction check is needed
                            add_entry(new_entry)
                    else:
                        st.warning("Please resolve the pending contradiction first.")

                except ValueError:
                    st.error("Invalid Time format. Please use YYYY-MM-DD HH:MM.")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")

# --- Contradiction Resolution UI ---
col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    if st.session_state.contradiction_pending_confirmation:
        st.subheader("Action Required: Contradiction Detected")
        st.markdown(f"The new entry for **{st.session_state.entry_to_confirm['Vessel_name']}** "
                    f"suggests **{st.session_state.entry_to_confirm['Laden/Ballst']}**, "
                    f"while recent entries were consistently **{st.session_state.previous_vessel_status}**.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, proceed with this change", key="confirm_yes"):
                add_entry(st.session_state.entry_to_confirm)
        with col2:
            if st.button("No, let me correct Laden/Ballast", key="confirm_no"):
                st.session_state.contradiction_pending_confirmation = False
                st.session_state.correcting_laden_ballast = True
                st.info("Please select the correct 'Laden/Ballst' status below.")
                st.rerun() # Rerun to show the correction input immediately

    elif st.session_state.correcting_laden_ballast:
        st.subheader("Correct 'Laden/Ballst' Status")
        
        # Default selection for correction: try to match the previous consistent status
        default_index = 0 if st.session_state.previous_vessel_status == 'Laden' else 1 
        
        corrected_laden_ballast = st.selectbox(
            "Select the correct 'Laden/Ballst' status:",
            options=['Laden', 'Ballast'],
            index=default_index, 
            key="corrected_laden_ballast_input"
        )
        if st.button("Confirm Correction", key="confirm_correction_btn"):
            st.session_state.entry_to_confirm['Laden/Ballst'] = corrected_laden_ballast
            add_entry(st.session_state.entry_to_confirm)

# Display current data with a button to show/hide
col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    if 'show_noon_data' not in st.session_state:
        st.session_state.show_noon_data = False
    if st.button("Show/Hide Current Noon Data", key="show_noon_data_btn"):
        st.session_state.show_noon_data = not st.session_state.show_noon_data
    if st.session_state.show_noon_data:
        st.header("Current Noon Data")
        st.dataframe(st.session_state.noon_data.style.format({'Time': lambda t: t.strftime('%Y-%m-%d %H:%M')}), use_container_width=True)