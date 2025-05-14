import streamlit as st

st.set_page_config(page_title="Payment", layout="centered")

st.markdown("### FAST LABOR")
st.markdown("## ")
st.markdown("## Payment")

# ตัวเลือกการชำระเงิน
payment_method = st.radio(
    "",
    ("Mobile Banking", "Credit card", "QR Code")
)

# ปุ่ม
col1, col2 = st.columns([1, 1])
with col1:
    cancel = st.button("Cancel")
with col2:
    confirm = st.button("Confirm")

# ✅ ถ้ากด Confirm แล้ว redirect ไป payment_success.py
if confirm:
    st.session_state["selected_payment_method"] = payment_method

    # แสดงข้อความก่อน redirect
    st.success(f"✅ คุณเลือกวิธีชำระเงิน: {payment_method}")
    st.markdown("กำลังดำเนินการ... กรุณารอสักครู่")

    # ✅ ใช้ HTML redirect แบบอัตโนมัติ
    st.markdown("""
        <meta http-equiv="refresh" content="0; url=./payment_success" />
    """, unsafe_allow_html=True)

# ✅ ถ้ากด Cancel
if cancel:
    st.warning("❌ ยกเลิกการชำระเงิน")
