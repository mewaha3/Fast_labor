import streamlit as st
# Must be first
st.set_page_config(page_title="Post Job", page_icon="📌", layout="centered")

import gspread
import json
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import uuid

# Load location data
@st.cache_data
def load_location_data():
    provinces = pd.read_json(
        "https://raw.githubusercontent.com/kongvut/thai-province-data/master/api_province.json"
    )
    districts = pd.read_json(
        "https://raw.githubusercontent.com/kongvut/thai-province-data/master/api_amphure.json"
    )
    subdistricts = pd.read_json(
        "https://raw.githubusercontent.com/kongvut/thai-province-data/master/api_tambon.json"
    )
    return provinces, districts, subdistricts

provinces, districts, subdistricts = load_location_data()

# Initialize session_state defaults
for key, default in {
    "province": "Select Province",
    "district": "Select District",
    "subdistrict": "Select Subdistrict",
    "zip_code": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Connect to Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    if "gcp" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(st.secrets.gcp.credentials), scope
        )
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("pages/credentials.json", scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("fastlabor")
    sheet = spreadsheet.worksheet("post_job")
except Exception as e:
    st.error(f"❌ Cannot connect to Google Sheets: {e}")
    st.stop()

# Check login
if not st.session_state.get("email"):
    st.warning("🔒 Please log in before posting a job.")
    st.stop()

# UI Header
st.page_link("pages/profile.py", label="Profile", icon="👤")
st.title("Post Job 📌")
st.image("image.png", width=400)

# Job Inputs
st.markdown("### Job Information")
job_type = st.text_input("Job Type *")
job_detail = st.text_area("Job Detail *")
salary = st.text_input("Wages *")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date *")
with col2:
    end_date = st.date_input("End Date *")
start_time = st.time_input("Start Time *")
end_time = st.time_input("End Time *")

# Address outside a frame
st.markdown("### Address Information")
job_address = st.text_area("Address (House No, Road, Soi.) *")

# Location cascade
st.markdown("### Location Details")
province_list = ["Select Province"] + provinces["name_th"].tolist()
province = st.selectbox("Province *", province_list, index=province_list.index(st.session_state.province))
if province != st.session_state.province:
    st.session_state.province = province
    st.session_state.district = "Select District"
    st.session_state.subdistrict = "Select Subdistrict"
    st.session_state.zip_code = ""

# District
district_list = ["Select District"]
if st.session_state.province != "Select Province":
    pid = provinces.loc[provinces.name_th == st.session_state.province, "id"].iloc[0]
    district_list += districts.loc[districts.province_id == pid, "name_th"].tolist()
district = st.selectbox("District *", district_list, index=district_list.index(st.session_state.district) if st.session_state.district in district_list else 0)
if district != st.session_state.district:
    st.session_state.district = district
    st.session_state.subdistrict = "Select Subdistrict"
    st.session_state.zip_code = ""

# Subdistrict and zip
sub_list = ["Select Subdistrict"]
zip_map = {}
if st.session_state.district != "Select District":
    did = districts.loc[districts.name_th == st.session_state.district, "id"].iloc[0]
    subs = subdistricts[subdistricts.amphure_id == did]
    sub_list += subs["name_th"].tolist()
    zip_map = subs.set_index("name_th")["zip_code"].to_dict()
subdistrict = st.selectbox(
    "Subdistrict *", sub_list,
    index=sub_list.index(st.session_state.subdistrict) if st.session_state.subdistrict in sub_list else 0
)
if subdistrict != st.session_state.subdistrict:
    st.session_state.subdistrict = subdistrict
    st.session_state.zip_code = zip_map.get(subdistrict, "")

st.text_input("Zip Code *", st.session_state.zip_code, disabled=True)

# Submit button at bottom
got_submit = st.button("Post Job")

if got_submit:
    try:
        profile_ws = spreadsheet.sheet1
        records = profile_ws.get_all_records()
        first_name = last_name = gender = ""
        for r in records:
            if r.get("email") == st.session_state.email:
                first_name = r.get("first_name", "")
                last_name = r.get("last_name", "")
                gender = r.get("gender", "")
                break
        existing = sheet.get_all_values()
        postjob_id = f"PJ{len(existing)}"
        job_date = f"{start_date} to {end_date}"
        sheet.append_row([
            postjob_id, first_name, last_name,gender, st.session_state.email,
            job_type, job_detail, salary, job_date,
            str(start_time), str(end_time), job_address,
            st.session_state.province, st.session_state.district,
            st.session_state.subdistrict, st.session_state.zip_code
        ])
        st.success(f"✅ Job posted successfully with ID: {postjob_id}")
    except Exception as e:
        st.error(f"❌ Error: {e}")

st.page_link("pages/home.py", label="Home", icon="🏠")

# List Job link
st.page_link("pages/list_job.py", label="List Job", icon="📄")