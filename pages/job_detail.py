import streamlit as st
from datetime import datetime
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# 1) Page Config
st.set_page_config(layout="centered")

# Header & Navigation
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
    <div><strong>FAST LABOR</strong></div>
    <div>
        <a href="#" style="margin-right: 20px;">Find Job</a>
        <a href="#" style="margin-right: 20px;">My Job</a>
        <a href="#" style="background-color: black; color: white; padding: 5px 10px; border-radius: 4px;">Profile</a>
    </div>
</div>
""", unsafe_allow_html=True)

# Title
st.markdown("## Job Detail")
st.image("image.png", width=150)

# 2) Connect to Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(st.secrets["gcp"]["credentials"]), scope
)
gc = gspread.authorize(creds)
sh = gc.open("fastlabor")

# 3) Load match_results sheet
ws = sh.worksheet("match_results")
records = ws.get_all_records()
match_results_df = pd.DataFrame(records)

# Get selected job
selected_job = st.session_state.get("selected_job", None)

if selected_job:
    # Use data from selected_job
    job_type = selected_job.get('job_type', '')
    job_title = selected_job.get('job_detail', '')  # Assuming 'job_detail' is the short title

    # Handle cases where the job_date might be a range
    job_date = selected_job.get('job_date', '')
    start_date_str = job_date.split(' to ')[0] if ' to ' in job_date else job_date
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None

    end_date_str = job_date.split(' to ')[1] if ' to ' in job_date else start_date_str
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

    start_time = datetime.strptime(selected_job.get('start_time', '08:00'), '%H:%M:%S').time()
    end_time = datetime.strptime(selected_job.get('end_time', '17:00'), '%H:%M:%S').time()
    job_address = f"{selected_job.get('subdistrict', '')}, {selected_job.get('district', '')}, {selected_job.get('province', '')}"
    
    # Default values for fields that shouldn't be editable
    job_salary = selected_job.get('job_salary', '500 THB')  # Default value
    salary_range = selected_job.get('job_salary', '500 - 700 THB')  # Default value

    # Fields that are fetched from match_results but not editable
    province = selected_job.get('province', '')
    district = selected_job.get('district', '')
    subdistrict = selected_job.get('subdistrict', '')
    gender = selected_job.get('gender', 'Any')  # Default to 'Any'

    # Job status (display as "In-Progress")
    job_status = "In-Progress"  # No selection box, just show as text

    # Display Job Status next to Job Type with a border
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Job Type", value=job_type, disabled=True)
    with col2:
        st.text_input("Job Status", value=job_status, disabled=True, label_visibility="collapsed")  # Hide label for consistency

    # Start and End Date, Start and End Time
    col3, col4 = st.columns(2)
    with col3:
        st.date_input("Start Date", value=start_date, disabled=True)
    with col4:
        st.date_input("End Date", value=end_date, disabled=True)

    col5, col6 = st.columns(2)
    with col5:
        st.time_input("Start Time", value=start_time, disabled=True)
    with col6:
        st.time_input("End Time", value=end_time, disabled=True)

    # Job Address
    st.text_area("Job Address (House No, Road, District)", value=job_address, disabled=True)

    # Province, District, Subdistrict, Gender
    col7, col8 = st.columns(2)
    with col7:
        st.text_input("Province", value=province, disabled=True)
    with col8:
        st.text_input("District", value=district, disabled=True)

    col9, col10 = st.columns(2)
    with col9:
        st.text_input("Subdistrict", value=subdistrict, disabled=True)
    with col10:
        st.text_input("Gender", value=gender, disabled=True)

    # Job Salary
    col11, = st.columns(1)  # Single column for Job Salary
    with col11:
        st.text_input("Job Salary", value=job_salary, disabled=True)

    # Selected Employees
    st.markdown("#### Employee")
    # Filter match_results_df to get employees for this job,  use findjob_id
    employees = match_results_df[match_results_df['findjob_id'] == selected_job.get('findjob_id')]
    if not employees.empty:
        for index, emp in employees.iterrows():
            st.write(f"👤 {emp.get('first_name', '')} {emp.get('last_name', '')}")
    else:
        st.write("No employees selected for this job.")

    # Payment Button
    st.page_link("pages/payment.py", label="💳 ชำระเงิน", icon="💰")

    # ✅ Job Done buttons (นายจ้าง และ ลูกจ้าง)
    col_done1, col_done2 = st.columns(2)

    def update_job_status(find_job_id, new_status):
        try:
            # Find the row by find_job_id
            row_index = match_results_df[match_results_df["findjob_id"] == find_job_id].index[0] + 2
            ws.update_cell(row_index, 11, new_status)  # Column 11 is 'status'
            st.success(f"Job status updated to {new_status}!")
        except IndexError:
            st.error(f"Could not find job with find_job_id: {find_job_id}")
        except Exception as e:
            st.error(f"An error occurred: {e}")

    with col_done1:
        if st.button("✅ Job Done นายจ้าง"):
            update_job_status(selected_job.get('findjob_id'), "Job Done")
            st.success("✅ Job details saved by employer!")
            st.markdown("""
                <meta http-equiv="refresh" content="0; url=./review_employee" />
            """, unsafe_allow_html=True)

    with col_done2:
        if st.button("🧑‍🔧 Job Done ลูกจ้าง"):
            update_job_status(selected_job.get('findjob_id'), "Job Done")
            st.success("🎉 Job details saved by employee!")
            st.markdown("""
                <meta http-equiv="refresh" content="0; url=./waiting_payment" />
            """, unsafe_allow_html=True)

    # Back to Homepage Button
    st.page_link("pages/home.py", label="Go to Homepage", icon="🏠")
else:
    st.info("Please select a job from the previous page.")
