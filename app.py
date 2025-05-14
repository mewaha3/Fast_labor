import streamlit as st
import gspread
import json
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ✅ ตั้งค่า Streamlit Page
st.set_page_config(page_title="Fast Labor Login", page_icon="", layout="centered")

# ✅ ตั้งค่า Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # ✅ โหลด credentials จาก Cloud (ผ่าน st.secrets) หรือ local
    if "gcp" in st.secrets and "credentials" in st.secrets["gcp"]:
        credentials_dict = json.loads(st.secrets["gcp"]["credentials"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("pages/credentials.json", scope)

    client = gspread.authorize(creds)
    sheet = client.open("fastlabor").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

except Exception as e:
    st.error(f"❌ ไม่สามารถเชื่อมต่อกับ Google Sheets: {e}")
    st.stop()

# ✅ ตั้งค่า session state
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "email" not in st.session_state:
    st.session_state["email"] = None
if "user_email" not in st.session_state:
    st.session_state["user_email"] = None

# ✅ แสดงโลโก้และข้อมูลเบื้องต้น
st.image("image.png", width=150)

st.markdown(
    """
    <h1 style='text-align: center;'>FAST LABOR</h1>
    <h3 style='text-align: center; color: gray;'>FAST JOB, FULL TRUST, GREAT WORKER</h3>
    <p style='text-align: center;'>แพลตฟอร์มที่เชื่อมต่อคนทำงานกับลูกค้าที่ต้องการแรงงานเร่งด่วน</p>
    """,
    unsafe_allow_html=True
)

# ✅ ฟังก์ชันตรวจสอบการล็อกอิน
def check_login(email, password):
    if "email" in df.columns and "password" in df.columns:
        user_data = df[(df["email"] == email) & (df["password"] == password)]
        return not user_data.empty
    return False

# ✅ ถ้า login แล้ว ให้ไปหน้า home.py
if st.session_state["logged_in"]:
    st.success(f"✅ Logged in as {st.session_state['email']}")

    st.page_link("pages/home.py", label="ไปหน้า Homepage")

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["email"] = None
        st.session_state["user_email"] = None
        st.experimental_rerun()

    st.stop()

# ✅ ฟอร์ม Login
st.markdown("<h2 style='text-align: center;'>LOGIN</h2>", unsafe_allow_html=True)

with st.form("login_form"):
    email = st.text_input("Email address/Username", placeholder="email@example.com")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    col1, col2 = st.columns([1, 3])
    with col1:
        login_button = st.form_submit_button("Submit")
    with col2:
        st.page_link("pages/reset_password.py", label="Forget password?", help="Click here to reset your password")

st.markdown("---")
st.markdown('<p style="text-align:center;">or</p>', unsafe_allow_html=True)
st.page_link("pages/register.py", label="New Register")

# ✅ ตรวจสอบการล็อกอิน
if login_button:
    if check_login(email, password):
        st.session_state["logged_in"] = True
        st.session_state["email"] = email
        st.session_state["user_email"] = email  # ✅ จำเป็นมาก สำหรับ profile.py
        st.success(f"Welcome, {email}!")

        # ✅ ไปหน้า home
        st.switch_page("pages/home.py")
    else:
        st.error("❌ Invalid email or password. Please try again.")
st.sidebar.button("🔍 Matching", on_click=st.experimental_set_query_params, args=(dict(page="match"),))

