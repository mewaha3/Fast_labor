import streamlit as st

# ✅ ต้องเรียกก่อนคำสั่งอื่นทั้งหมด
st.set_page_config(page_title="New Member Registration", page_icon="📝", layout="centered")

import json
import pandas as pd
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ✅ โหลดข้อมูลจังหวัด อำเภอ ตำบล และรหัสไปรษณีย์
@st.cache_data
def load_location_data():
    url_province = "https://raw.githubusercontent.com/kongvut/thai-province-data/master/api_province.json"
    url_district = "https://raw.githubusercontent.com/kongvut/thai-province-data/master/api_amphure.json"
    url_subdistrict = "https://raw.githubusercontent.com/kongvut/thai-province-data/master/api_tambon.json"

    provinces = pd.read_json(url_province)
    districts = pd.read_json(url_district)
    subdistricts = pd.read_json(url_subdistrict)

    return provinces, districts, subdistricts

provinces, districts, subdistricts = load_location_data()

# ✅ ตั้งค่า session_state สำหรับ dropdown ที่เกี่ยวข้อง
for key, default in {
    "selected_province": "Select Province",
    "selected_district": "Select District",
    "selected_subdistrict": "Select Subdistrict",
    "zip_code": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ✅ ตั้งค่า Google Sheets API (Cloud หรือ Local)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    if "gcp" in st.secrets and "credentials" in st.secrets["gcp"]:
        credentials_dict = json.loads(st.secrets["gcp"]["credentials"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("pages/credentials.json", scope)

    client = gspread.authorize(creds)
    sheet = client.open("fastlabor").sheet1  # เปลี่ยนเป็นชื่อ Google Sheets ของคุณ

except Exception as e:
    st.error(f"❌ ไม่สามารถเชื่อมต่อกับ Google Sheets: {e}")
    st.stop()

# ✅ ส่วน UI
st.image("image.png", width=150)
st.title("New Member Registration")

st.markdown("#### Personal Information")
first_name = st.text_input("First name *")
last_name = st.text_input("Last name *")
national_id = st.text_input("National ID *")

if national_id and (not national_id.isdigit() or len(national_id) != 13):
    st.error("❌ National ID ต้องเป็นตัวเลข 13 หลักเท่านั้น")

dob = st.date_input("Date of Birth *")
gender = st.selectbox("Gender *", ["Male", "Female", "Other"])
nationality = st.text_input("Nationality *")

# ✅ ที่อยู่
st.markdown("#### Address Information")
address = st.text_area("Address (House Number, Road, Soi.) *")

province_names = ["Select Province"] + provinces["name_th"].tolist()
selected_province = st.selectbox("Province *", province_names, index=province_names.index(st.session_state.selected_province))

if selected_province != st.session_state.selected_province:
    st.session_state.selected_province = selected_province
    st.session_state.selected_district = "Select District"
    st.session_state.selected_subdistrict = "Select Subdistrict"
    st.session_state.zip_code = ""
    st.rerun()

# ✅ District
if selected_province != "Select Province":
    province_id = provinces[provinces["name_th"] == selected_province]["id"].values[0]
    filtered_districts = ["Select District"] + districts[districts["province_id"] == province_id]["name_th"].tolist()
else:
    filtered_districts = ["Select District"]

selected_district = st.selectbox("District *", filtered_districts, index=filtered_districts.index(st.session_state.selected_district))

if selected_district != st.session_state.selected_district:
    st.session_state.selected_district = selected_district
    st.session_state.selected_subdistrict = "Select Subdistrict"
    st.session_state.zip_code = ""
    st.rerun()

# ✅ Subdistrict + Zip code
if selected_district != "Select District":
    district_id = districts[districts["name_th"] == selected_district]["id"].values[0]
    filtered_subdistricts = subdistricts[subdistricts["amphure_id"] == district_id]

    subdistrict_names = ["Select Subdistrict"] + filtered_subdistricts["name_th"].tolist()
    zip_codes = filtered_subdistricts.set_index("name_th")["zip_code"].to_dict()
else:
    subdistrict_names = ["Select Subdistrict"]
    zip_codes = {}

selected_subdistrict = st.selectbox("Subdistrict *", subdistrict_names, index=subdistrict_names.index(st.session_state.selected_subdistrict))

if selected_subdistrict != st.session_state.selected_subdistrict:
    st.session_state.selected_subdistrict = selected_subdistrict
    st.session_state.zip_code = zip_codes.get(selected_subdistrict, "")
    st.rerun()

zip_code = st.text_input("Zip Code *", st.session_state.zip_code, disabled=True)

# ✅ Email + Password
st.markdown("#### Account Information")
email = st.text_input("Email address *")
password = st.text_input("Password *", type="password")

# ✅ ตรวจสอบว่ากรอกครบ
required_fields = [
    first_name, last_name, national_id, dob, gender, nationality,
    address, selected_province, selected_district, selected_subdistrict,
    st.session_state.zip_code, email, password
]

all_fields_filled = all(bool(str(field).strip()) for field in required_fields)

submit_button = st.button("Submit", disabled=not all_fields_filled)

# ✅ บันทึกข้อมูลเมื่อกด Submit และไปหน้า upload.py ทันที
if submit_button:
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sheet.append_row([
            first_name, last_name, national_id, str(dob), gender, nationality,
            address, selected_province, selected_district, selected_subdistrict,
            st.session_state.zip_code, email, password, timestamp
        ])

        st.success("✅ ลงทะเบียนสำเร็จ!")
        st.session_state["user_email"] = email

        # ✅ เปลี่ยนหน้าไป upload.py ทันที
        st.switch_page("pages/upload.py")

    except Exception as e:
        st.error(f"❌ ไม่สามารถบันทึกข้อมูลได้: {e}")

# ✅ ปุ่มย้อนกลับ
st.page_link("app.py", label="⬅️ Back to Login", icon="🔙")
