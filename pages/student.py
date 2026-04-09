import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner
from utils import verify_qr_token
from database import get_connection
from datetime import datetime
import streamlit.components.v1 as components


def show():
    st.title("📱 Student Attendance Scanner")

    # ── Location display (JS only, no Python parsing) ──
    st.subheader("📍 Your Location")
    components.html("""
        <div id="status" style="font-family:sans-serif; font-size:15px; padding:6px;">
            ⏳ Requesting location...
        </div>
        <script>
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(pos) {
                    document.getElementById("status").innerHTML =
                        "✅ Lat: <b>" + pos.coords.latitude.toFixed(6) + "</b> | " +
                        "Lon: <b>" + pos.coords.longitude.toFixed(6) + "</b> | " +
                        "Accuracy: <b>" + pos.coords.accuracy.toFixed(0) + "m</b>";
                },
                function(err) {
                    document.getElementById("status").innerText = "❌ " + err.message;
                },
                { enableHighAccuracy: true, timeout: 15000 }
            );
        } else {
            document.getElementById("status").innerText = "❌ Geolocation not supported.";
        }
        </script>
    """, height=40)

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