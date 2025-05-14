import streamlit as st
import pandas as pd
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from gspread_dataframe import set_with_dataframe

# 1) Page config & guard
st.set_page_config(page_title="Result Matching | FAST LABOR", layout="centered")
if not st.session_state.get("logged_in", False):
    st.stop()

st.title("🔍 AI Matching – ผลการจับคู่")

active_job_idx: int | None = st.session_state.get("job_idx")
active_seeker_idx: int | None = st.session_state.get("seeker_idx")

if active_job_idx is None and active_seeker_idx is None:
    st.info("กรุณากลับไปเลือกงาน/ผู้สมัครจากหน้า My Jobs ก่อนค่ะ")
    st.stop()

# -----------------------------------------------------------------
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
    df = pd.DataFrame(vals[1:], columns=vals[0])
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

# -----------------------------------------------------------------
# Load & encode data
import matching  # Ensure you have the matching.py file with the necessary functions
jobs_df = matching.encode_job_df(_sheet_df("post_job"))
seekers_df = matching.encode_worker_df(_sheet_df("find_job"))

# -----------------------------------------------------------------
# Utility: compute avg salary
def avg_salary(row: pd.Series) -> str:
    try:
        s = float(row.get("start_salary") or row.get("salary") or 0)
        r = float(row.get("range_salary") or row.get("salary") or 0)
        if s or r:
            return f"{(s + r) / 2:.0f}"
    except:
        pass
    return "-"

# -----------------------------------------------------------------
# Prepare match_results sheet headers
def _get_match_ws():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp"]["credentials"]),
        ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    gc = gspread.authorize(creds)
    ws = gc.open("fastlabor").worksheet("match_results")
    return ws, ws.row_values(1)

# -----------------------------------------------------------------
# 4) Employer view: show Top-5 seekers & choose priority
if active_job_idx is not None:
    job_row_encoded = jobs_df.iloc[active_job_idx]
    top5 = matching.recommend_seekers(job_row_encoded, seekers_df, n=5)

    raw_seek = _sheet_df("find_job")
    raw_jobs_df = _sheet_df("post_job") # Load post_job data here

    priority = {}
    for rank, rec in enumerate(top5.itertuples(index=False), start=1):
        st.divider()
        raw = raw_seek[raw_seek.email == rec.email].iloc[0]
        name = f"{raw.first_name} {raw.last_name}".strip() or "-"
        gender = raw.gender or "-"
        date = raw.job_date or "-"
        time = f"{raw.start_time} – {raw.end_time}"
        loc = f"{raw.province}/{raw.district}/{raw.subdistrict}"
        sal = avg_salary(raw)
        col1, col2 = st.columns([4,1])
        with col1:
            st.markdown(f"**Employee No.{rank}**")
            st.markdown(f"- **Name**: {name}")
            st.markdown(f"- **Gender**: {gender}")
            st.markdown(f"- **Job Type**: {rec.job_type}")
            st.markdown(f"- **Date**: {date}")
            st.markdown(f"- **Time**: {time}")
            st.markdown(f"- **Location**: {loc}")
            st.markdown(f"- **Salary**: {sal}")
        with col2:
            priority[rank] = st.selectbox("Priority", [1,2,3,4,5], index=rank-1, key=f"prio_{rank}")

    if st.button("✅ Confirm Matches", use_container_width=True):
        ws_tuple = _get_match_ws()
        ws = ws_tuple[0]
        headers_in_sheet = [h.lower().strip() for h in ws_tuple[1]] # ดึง Header จาก Sheet และปรับให้เป็น lowercase และไม่มีช่องว่าง

        match_data = []
        for rank, rec in enumerate(top5.itertuples(index=False), start=1):
            # Find matching raw seeker
            raw_seeker = raw_seek[raw_seek.email == rec.email].iloc[0].to_dict()
            # Find matching raw job to get salary
            raw_job = raw_jobs_df[raw_jobs_df.job_id == job_row_encoded.job_id].iloc[0]
            job_salary = raw_job.get("salary", "")

            match_data_row = raw_seeker.copy()
            match_data_row['priority'] = priority.get(rank, 1)
            match_data_row['status'] = 'on queue'
            match_data_row['find_job_id'] = top5.index[rank - 1]
            match_data_row['job_salary'] = job_salary
            
            match_data.append(match_data_row)

        if match_data:
            df_to_upload = pd.DataFrame(match_data)
            cols_to_upload = [col.lower().strip() for col in df_to_upload.columns] # ปรับชื่อคอลัมน์ที่จะอัปโหลด

            # สร้าง DataFrame ใหม่โดยใช้เฉพาะคอลัมน์ที่มีอยู่ใน Sheet และเรียงตามลำดับใน Sheet
            cols_to_upload_existing = [col for col in cols_to_upload if col in headers_in_sheet]
            df_upload = df_to_upload[df_to_upload.columns[df_to_upload.columns.str.lower().str.strip().isin(cols_to_upload_existing)]]
            df_upload = df_upload[sorted(df_upload.columns, key=lambda col: headers_in_sheet.index(col.lower().strip()))]

            # หาแถวสุดท้ายที่มีข้อมูลเพื่อเขียนต่อท้าย
            last_row = len(ws.get_all_values()) + 1
            # ลองใช้วิธีเขียนข้อมูลโดยตรงด้วย gspread
            data_to_write = df_upload.values.tolist()
            cell_range = f"A{last_row}:{chr(ord('A') + len(df_upload.columns) - 1)}{last_row + len(data_to_write) - 1}"
            ws.update(cell_range, data_to_write)
            st.success("🎉 บันทึกผลการจับคู่เรียบร้อยแล้ว!")
        else:
            st.info("ไม่มีรายการจับคู่ที่จะบันทึก")

# -----------------------------------------------------------------
# 5) Worker view: show Top-5 jobs
elif active_seeker_idx is not None:
    seeker_row_encoded = seekers_df.iloc[active_seeker_idx]
    top5 = matching.recommend(seeker_row_encoded, jobs_df, n=5)

    raw_jobs = _sheet_df("post_job")

    st.subheader("📋 งานแนะนำสำหรับคุณ")
    for rank, rec in enumerate(top5.itertuples(index=False), start=1):
        st.divider()
        raw = raw_jobs[raw_jobs.job_id == rec.job_id].iloc[0]
        job_type = rec.job_type or "-"
        date = raw.job_date or "-"
        time = f"{raw.start_time} – {raw.end_time}"
        loc = f"{raw.province}/{raw.district}/{raw.subdistrict}"
        sal = avg_salary(raw)
        st.markdown(f"**Job No.{rank}**")
        st.markdown(f"- **Job Type**: {job_type}")
        st.markdown(f"- **Date**: {date}")
        st.markdown(f"- **Time**: {time}")
        st.markdown(f"- **Location**: {loc}")
        st.markdown(f"- **Salary**: {sal} THB")
        

# -----------------------------------------------------------------
st.divider()
if st.button("🔙 กลับหน้า My Jobs"):
    st.switch_page("pages/list_job.py")
