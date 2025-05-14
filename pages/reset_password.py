import streamlit as st
import gspread
import json
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ✅ ตั้งค่า Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # ✅ โหลด Credentials จาก Streamlit Secrets (สำหรับ Cloud)
    if "gcp" in st.secrets:
        credentials_dict = json.loads(st.secrets["gcp"]["credentials"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    else:
        # ✅ โหลด Credentials จากไฟล์ (สำหรับ Local)
        creds = ServiceAccountCredentials.from_json_keyfile_name("pages/credentials.json", scope)

    # ✅ เชื่อมต่อ Google Sheets
    client = gspread.authorize(creds)
    sheet = client.open("fastlabor").sheet1  # เปลี่ยนเป็นชื่อ Google Sheets ของคุณ

    # ✅ โหลดข้อมูลทั้งหมดจาก Google Sheets
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

except Exception as e:
    st.error(f"❌ ไม่สามารถเชื่อมต่อกับ Google Sheets: {e}")
    st.stop()

# ✅ ตั้งค่าหน้า Streamlit
st.set_page_config(page_title="Reset Password", page_icon="🔑", layout="centered")

st.title("Reset Password")

# ✅ ฟอร์มรีเซ็ตรหัสผ่าน
with st.form("reset_password_form"):
    email = st.text_input("Email", placeholder="Enter your email")
    new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter new password")
    
    submit_button = st.form_submit_button("Reset Password")

# ✅ ถ้ากดปุ่ม Reset Password
if submit_button:
    if not email or not new_password or not confirm_password:
        st.error("❌ Please fill in all fields.")
    elif new_password != confirm_password:
        st.error("❌ Passwords do not match. Please try again.")
    else:
        # ✅ ตรวจสอบว่าอีเมลมีอยู่ในระบบหรือไม่
        if email in df["email"].values:
            try:
                # ✅ ค้นหาแถวที่ต้องอัปเดตรหัสผ่าน
                row_index = df[df["email"] == email].index[0] + 2  # แถวใน Google Sheets (index เริ่มที่ 0 + header)
                
                # ✅ อัปเดตรหัสผ่านใหม่
                sheet.update_cell(row_index, df.columns.get_loc("password") + 1, new_password)

                st.success("✅ Password updated successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
        else:
            st.error("❌ Email not found. Please try again.")

# ✅ ปุ่มกลับหน้า Login
st.page_link("app.py", label="Go to Login", icon="🔑")
