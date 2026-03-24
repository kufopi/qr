import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner
from streamlit_geolocation import streamlit_geolocation
from utils import verify_qr_token
from database import get_connection
from datetime import datetime


def show():
    st.title("📱 Student Attendance Scanner")

    # ── Location Debug ──
    st.subheader("📍 Your Location")
    location = streamlit_geolocation()

    if location and location.get("latitude") is not None:
        lat = location["latitude"]
        lon = location["longitude"]
        accuracy = location.get("accuracy", "?")
        st.success(f"✅ Location acquired!")
        col1, col2, col3 = st.columns(3)
        col1.metric("Latitude", f"{lat:.6f}")
        col2.metric("Longitude", f"{lon:.6f}")
        col3.metric("Accuracy", f"{accuracy:.0f}m" if isinstance(accuracy, float) else f"{accuracy}m")
        st.map({"lat": [lat], "lon": [lon]})
    else:
        st.warning("⏳ Waiting for location... Please allow browser location permission.")

    st.divider()

    # ── Scanner ──
    st.subheader("Scan the Projected QR Code")
    qr_data = qrcode_scanner(key="scanner")

    if qr_data:
        st.info("🔍 QR scanned. Processing...")

        token = qr_data.strip()
        payload = verify_qr_token(token)

        if not payload:
            st.error("❌ QR code is expired or invalid. Ask the lecturer to refresh it.")
            return

        session_id = payload["session_id"]

        conn = get_connection()
        c = conn.cursor()

        c.execute("SELECT id FROM sessions WHERE id=?", (session_id,))
        if not c.fetchone():
            st.error("❌ Session not found. Make sure the lecturer has started a session.")
            conn.close()
            return

        c.execute(
            "SELECT 1 FROM attendance WHERE session_id=? AND student_username=?",
            (session_id, st.session_state.username),
        )
        if c.fetchone():
            st.warning("⚠️ You have already been marked present for this session.")
            conn.close()
            return

        c.execute(
            "INSERT INTO attendance VALUES (NULL, ?, ?, ?, 'Present')",
            (session_id, st.session_state.username, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        st.success("✅ Attendance Marked Successfully!")
        st.balloons()