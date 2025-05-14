import streamlit as st

# ตั้งค่าหน้า
st.set_page_config(page_title="Payment Success", layout="centered")

# หัวเรื่อง
st.markdown("### FAST LABOR")
st.markdown("## ✅ Payment Success")

# แสดงวิธีชำระเงินที่เลือก (ถ้ามี)
if "selected_payment_method" in st.session_state:
    st.write(f"คุณเลือกวิธีชำระเงิน: **{st.session_state['selected_payment_method']}**")

# เว้นระยะห่างเล็กน้อย
st.markdown("")

# ปุ่มไปหน้า job_detail
st.markdown("### ไปสรุปผลการจ้างงาน")

if st.button("📄 ดูรายละเอียดการจ้างงาน"):
    st.switch_page("pages/job_detail.py")
