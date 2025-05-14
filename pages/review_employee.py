import streamlit as st

st.set_page_config(layout="centered")

# Header & Navigation
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <div><strong>FAST LABOR</strong></div>
    <div>
        <a href="#" style="margin-right: 20px;">Find Job</a>
        <a href="#" style="margin-right: 20px;">My Job</a>
        <a href="#" style="background-color: black; color: white; padding: 5px 10px; border-radius: 4px;">Profile</a>
    </div>
</div>
""", unsafe_allow_html=True)

# Title
st.markdown("## ⭐ Review Employee")

# Form input
st.markdown("### ให้คะแนนและแสดงความคิดเห็น")

rating = st.slider("ให้คะแนน", min_value=1, max_value=5, value=3)
comment = st.text_area("ความคิดเห็นเพิ่มเติม", placeholder="แสดงความคิดเห็นเกี่ยวกับพนักงานที่ทำงานให้คุณ")

# ปุ่ม Submit
if st.button("Submit Review"):
    st.success("✅ ขอบคุณสำหรับการรีวิว!")
    
    # แสดงผลลัพธ์ที่ผู้ใช้กรอก
    stars_display = "⭐" * rating + "☆" * (5 - rating)
    st.markdown("---")
    with st.container():
        st.markdown(f"""
        <div style="display: flex; justify-content: center;">
          <div style="border: 1px solid #ddd; border-radius: 12px; padding: 20px; width: 300px; text-align: center;">
            <div style="font-size: 22px; color: #ffcc00;">{stars_display}</div>
            <h4 style="margin-top: 10px;">Review</h4>
            <p style="color: #555;">{comment if comment else 'ไม่มีความคิดเห็นเพิ่มเติม'}</p>
            <div style="display: flex; align-items: center; justify-content: center; margin-top: 15px;">
                <img src="https://randomuser.me/api/portraits/women/44.jpg" width="30" style="border-radius: 50%; margin-right: 10px;" />
                <div style="text-align: left;">
                    <div style="font-weight: bold;">คุณลูกค้า</div>
                    <div style="font-size: 12px; color: gray;">Client</div>
                </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
st.page_link("pages/home.py", label="Go to Homepage", icon="🏠")

