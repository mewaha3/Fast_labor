import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# 1) Page config & header
st.set_page_config(page_title="Status Matching | FAST LABOR", layout="centered")
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <div><strong>FAST LABOR</strong></div>
    <div>
        <a href="pages/find_job_matching.py" style="margin-right: 20px;">Find Job</a>
        <a href="pages/list_job.py" style="margin-right: 20px;">My Job</a>
        <a href="pages/profile.py" style="background-color: black; color: white; padding: 5px 10px; border-radius: 4px;">Profile</a>
    </div>
</div>
""", unsafe_allow_html=True)

st.title("📊 Status Matching")

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
df = pd.DataFrame(records)

# 4) Helper: status color
def get_status_color(status: str) -> str:
    s = (status or "").lower()
    return "green" if s == "accepted" else \
           "orange" if s == "on queue" else \
           "red" if s == "declined" else \
           "gray"

if df.empty:
    st.info("ยังไม่มีข้อมูลแมตช์")
else:
    st.markdown("---")
    # Select only the first 5 results
    top_5_matches = df.head(5)  # This limits the DataFrame to the first 5 rows
    
    for index, row in top_5_matches.iterrows():
        employee_no = index + 1
        name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() or '-'
        gender = row.get('gender', '') or '-'
        job_type = row.get('job_type', '') or ''
        date = row.get('job_date', '') or '-'
        time = f"{row.get('start_time', '') or ''} – {row.get('end_time', '') or ''}"
        location = f"{row.get('province', '')}/{row.get('district', '')}/{row.get('subdistrict', '')}".rstrip('/') or '-'
        salary = row.get('job_salary', '') or '-'
        priority = row.get('priority', '') or '-'
        status = row.get('status', '') or 'No Status'
        find_job_id = row.get('findjob_id', '') or ''
        job_detail_data = row.to_dict() # ดึงข้อมูลทั้งหมดของแถวเพื่อส่งไปยังหน้า Job Detail

        st.markdown(f"**Employee No.{employee_no}**")
        st.markdown(f"- **Name:** {name}")
        st.markdown(f"- **Gender:** {gender}")
        st.markdown(f"- **Job Type:** {job_type}")
        st.markdown(f"- **Date:** {date}")
        st.markdown(f"- **Time:** {time}")
        st.markdown(f"- **Location:** {location}")
        st.markdown(f"- **Salary:** {salary}")
        st.markdown(f"- **Priority:** {priority}")

        col1, col2 = st.columns([3, 1])
        with col1:
            color = get_status_color(status)
            st.markdown(
                f"<span style='padding:4px 8px; background-color:{color}; color:white; border-radius:4px;'>"
                f"{status}"
                f"</span>", unsafe_allow_html=True
            )
        with col2:
            if status.lower() == "accepted":
                if st.button("ดูรายละเอียด", key=f"job_detail_{find_job_id}"):
                    st.session_state["selected_job"] = job_detail_data
                    st.switch_page("pages/job_detail.py")

        st.markdown("---")

# 5) Back to My Jobs button
if st.button("🔙 กลับหน้า My Jobs"):
    st.switch_page("pages/list_job.py")
