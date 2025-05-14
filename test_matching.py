# เปิด Python shell หรือสร้างไฟล์ test_matching.py แล้วรันด้วย python test_matching.py
import pandas as pd
import matching

# 1) โหลดข้อมูลจาก CSV (ต้องอยู่ในไดเรกทอรีเดียวกับ matching.py)
jobs_df    = matching.encode_job_df(pd.read_csv("post_job.csv"))
seekers_df = matching.encode_worker_df(pd.read_csv("find_job.csv"))

# 2) เลือกแรงงานตัวอย่าง (เช่น แถวแรก)
worker_row = seekers_df.iloc[0]

# 3) เรียก recommend()
recs = matching.recommend(worker_row, jobs_df, n=5)

# 4) แสดงค่า sim และ ai_score
print("sim       :", recs["sim"].tolist())
print("ai_score  :", recs["ai_score"].tolist())
