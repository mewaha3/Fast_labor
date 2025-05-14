import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1) Page Config
st.set_page_config(layout="centered")

# Header & Navigation
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <div><strong>FAST LABOR</strong></div>
    <div>
        <a href="#" style="margin-right: 20px;">Find Job</a>
        <a href="#" style="margin-right: 20px;">My Job</a>
        <a href="#" style="background-color: black; color: white; padding: 5px 10px; border-radius: 4px;">Profile</a>
    </div>
</div>
""", unsafe_allow_html=True)

# Title
st.markdown("## Find Job")
st.markdown("For generating a list of employees who were matching with the job")

# Image
st.image("image.png", width=150)

# Get the logged-in user's email
logged_in_email = st.session_state.get("email", None)

if not logged_in_email:
    st.error("❌ Please log in to view your matching jobs.")
    st.stop()

# ------------------------------------------------------------------
# Helper: load sheet to df
def _sheet_df(name: str) -> pd.DataFrame:
    SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp"]["credentials"]), SCOPE
    )
    gc = gspread.authorize(creds)
    ws = gc.open("fastlabor").worksheet(name)
    vals = ws.get_all_values()
    st.write(f"First row of {name}: {vals[0] if vals else 'No data'}")  # Debugging
    df = pd.DataFrame(vals[1:], columns=vals[0])
    if not df.empty and isinstance(df.columns, pd.Index):
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    elif not df.empty:
        # If df.columns is not a Pandas Index, try to convert it to a list of strings
        try:
            df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
        except Exception as e:
            st.error(f"Error cleaning column names: {e}")
    return df

# Helper: update status in Google Sheet
def _update_match_status(find_job_id: str, status: str):
    SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp"]["credentials"]), SCOPE
    )
    gc = gspread.authorize(creds)
    ws = gc.open("fastlabor").worksheet("match_results")

    match_results_df = _sheet_df("match_results")  # Get the latest data
    st.write(f"Updating find_job_id: {find_job_id}, status: {status}")  # Debugging

    try:
        # Try to find the row index for the given job ID
        row_index = match_results_df[match_results_df["findjob_id"] == find_job_id].index[0] + 2  # +2 to adjust for header and 0-based index
        st.write(f"Row index: {row_index}")  # Debugging

        # Check if the row_index is valid
        if row_index > len(match_results_df) + 1:
            st.error(f"Invalid row index: {row_index}. The row does not exist.")
            return

        # Column O is where the 'status' should be. Update if necessary.
        status_column_letter = 'O'  # Column O is where the 'status' should be. Change if needed.

        # Debugging: Check the value being updated
        st.write(f"Updating cell {status_column_letter}{row_index} with value: {status}")

        # Ensure the status is a valid text string and not an empty value
        if status not in ["Accepted", "Declined"]:
            st.error(f"Invalid status value: {status}. Expected 'Accepted' or 'Declined'.")
            return

        # Update the status in Google Sheets
        ws.update(f"{status_column_letter}{row_index}", status)
        st.success(f"Status for Job ID '{find_job_id}' updated to '{status}'!")
    except IndexError:
        st.error(f"Could not find job with ID: {find_job_id}")
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.write(f"Error details: {e}")

# Load match_results sheet
match_results_df = _sheet_df("match_results")
st.write("Head of match_results_df:")  # Debugging
st.write(match_results_df.head())  # Debugging

# Get the logged-in user's email
logged_in_email = st.session_state.get("email", None)
st.write(f"Logged in email: {logged_in_email}")  # Debugging

# Filter match results by the logged-in user's email
matching_jobs = match_results_df[match_results_df["email"] == logged_in_email]

if matching_jobs.empty:
    st.info("❌ No matching jobs found for your profile.")
else:
    # Display matching jobs with Accept/Decline buttons
    for index, job in matching_jobs.iterrows():
        with st.container():
            find_job_id = job.get('findjob_id', 'N/A')
            st.markdown(f"### Job #{find_job_id}")
            st.write(f"ประเภทงาน: {job.get('job_type', 'N/A')}")
            st.write(f"รายละเอียด: {job.get('job_detail', 'N/A')}")
            st.write(f"วันเวลา: {job.get('job_date', 'N/A')} | {job.get('start_time', 'N/A')} - {job.get('end_time', 'N/A')}")
            st.write(f"สถานที่: {job.get('province', 'N/A')}/{job.get('district', 'N/A')}/{job.get('subdistrict', 'N/A')}")
            st.write(f"ช่วงรายได้: {job.get('job_salary', 'N/A')} THB/day")

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Decline", key=f"decline_{find_job_id}"):
                    _update_match_status(find_job_id, "Declined")
                    st.rerun()  # Refresh the page to reflect the change

            with col2:
                if st.button("Accept", key=f"accept_{find_job_id}"):
                    _update_match_status(find_job_id, "Accepted")
                    st.session_state["selected_job"] = job.to_dict()  # Send job info to the next page
                    st.switch_page("pages/job_detail.py")  # Go to job_detail.py

            st.markdown("---")

# Refresh Button
st.markdown("""
    <div style='text-align: center; margin-top: 30px;'>
        <button style='background-color: black; color: white; padding: 10px 30px; border-radius: 5px; font-weight: bold;'>
            Refresh Find Job
        </button>
    </div>
""", unsafe_allow_html=True)
