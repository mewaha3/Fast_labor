import streamlit as st

# ✅ ตั้งค่าหน้า
st.set_page_config(page_title="Verification Result", page_icon="✅", layout="centered")

st.image("image.png", width=150)
st.title("Result verification")

st.markdown("<h2 style='color:green; text-align:center;'>Pass Verification</h2>", unsafe_allow_html=True)

# ✅ ปุ่มไปหน้า Profile
st.page_link("pages/profile.py", label="Go to Profile", icon="👤")
st.page_link("pages/home.py", label="Go to Home", icon="🏠")
