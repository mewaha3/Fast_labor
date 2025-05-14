# pages/review_matched.py
"""
หน้า Review Matched (นายจ้าง)
--------------------------------
• แสดงรายชื่อแรงงานที่ AI แนะนำสำหรับงานที่เลือก
• นายจ้างสามารถกำหนด Priority แล้วกด Invite
• Invite = บันทึกลง Google Sheet `matches` (status = invited)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import gspread
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# ------------------------------------------------------------------
# 0) Guard: ต้อง Login และมี job_idx & recs ใน session
# ------------------------------------------------------------------
if not st.session_state.get("logged_in", False):
    st.error("กรุณา Login ก่อน")
    st.stop()

job_idx: int | None = st.session_state.get("job_idx")
recs: pd.DataFrame | None = st.session_state.get("recs_df")  # จาก Result Matching.py

if job_idx is None or recs is None:
    st.warning("กรุณาเลือกงานและดูผล AI Matching ก่อน")
    st.page_link("pages/Result Matching.py", "ดูผล AI Matching ➜")
    st.stop()

# ------------------------------------------------------------------
# 1) กำหนด Google‑Sheets helper
# ------------------------------------------------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds_json = json.loads(st.secrets["gcp"]["credentials"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
client = gspread.authorize(creds)
sh = client.open("fastlabor")

jobs_ws     = sh.worksheet("post_job")
matches_ws  = sh.worksheet("matches")

# รับข้อมูล row งานนี้
jobs_df = pd.DataFrame(jobs_ws.get_all_values()[1:], columns=jobs_ws.get_all_values()[0])
job_row = jobs_df.iloc[job_idx]

st.title("📋 Review Matched – ตรวจรายชื่อแรงงาน")
st.markdown(f"**งาน** : `{job_row['job_type']}` วันที่ {job_row['job_date']}  (Job‑ID: {job_row['job_id']})")

# ------------------------------------------------------------------
# 2) Loop แสดงแรงงานที่แนะนำ
# ------------------------------------------------------------------
invited_cnt = 0

for i, row in recs.iterrows():
    with st.expander(f"{i+1}. {row['worker_id']} – {row['job_type']}"):
        st.write(f"- **Email** : {row['email']}")
        st.write(f"- **Expected Wage** : {row['exp_wage']:.0f} THB")
        st.write(f"- **AI Score** : {row['ai_score']:.3f}")

        pr = st.selectbox("Priority", [1, 2, 3, 4, 5], key=f"prio_{i}")
        if st.button("📨 Invite", key=f"invite_{i}"):
            # สร้าง match_id วนซ้ำไม่ซ้ำ
            match_id = str(uuid.uuid4())[:8]
            matches_ws.append_row([
                match_id,
                job_row["job_id"],
                row["worker_id"],
                pr,
                "invited",
                f"{row['ai_score']:.4f}",
                datetime.utcnow().isoformat(sep=" ", timespec="seconds")
            ])
            st.success("ส่งคำเชิญสำเร็จ!")
            invited_cnt += 1

if invited_cnt:
    st.toast(f"ส่งคำเชิญแล้ว {invited_cnt} คน", icon="✅")
    st.page_link("pages/list_job.py", label="กลับหน้า My Jobs ➜")
