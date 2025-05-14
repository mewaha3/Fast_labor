# pages/login.py

import streamlit as st
import gspread, json
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Login | FAST LABOR", layout="centered")
st.title("🔑 FAST LABOR Login")

# 1. Load users sheet
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
if "gcp" in st.secrets:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp"]["credentials"]), scope)
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name("pages/credentials.json", scope)
gc = gspread.authorize(creds)
df = pd.DataFrame(gc.open("fastlabor").worksheet("register").get_all_records())

# 2. Session init
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 3. If already logged in → go home
if st.session_state.logged_in:
    st.success(f"Welcome back, {st.session_state.email}")
    st.page_link("pages/home.py", label="Go to Home →")
    st.stop()

# 4. Login form
email = st.text_input("Email")
pwd   = st.text_input("Password", type="password")
if st.button("Log In"):
    user = df[(df.email==email)&(df.password==pwd)]
    if not user.empty:
        st.session_state.logged_in = True
        st.session_state.email     = email
        st.success("Login successful")
        st.page_link("pages/home.py", label="Continue →")
    else:
        st.error("Invalid email or password")
