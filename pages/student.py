import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner
from utils import verify_qr_token
from database import get_connection
from datetime import datetime
import streamlit.components.v1 as components
import json


def get_location():
    """Use a plain HTML/JS component instead of streamlit_geolocation to avoid asyncio errors."""
    location_html = """
        <div id="status" style="font-family:sans-serif; padding:8px;">
            ⏳ Requesting location...
        </div>
        <script>
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(pos) {
                    const data = {
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude,
                        accuracy: pos.coords.accuracy
                    };
                    document.getElementById("status").innerText =
                        "✅ Lat: " + data.latitude.toFixed(6) +
                        " | Lon: " + data.longitude.toFixed(6) +
                        " | Accuracy: " + data.accuracy.toFixed(0) + "m";
                    window.parent.postMessage({type: "streamlit:setComponentValue", value: data}, "*");
                },
                function(err) {
                    document.getElementById("status").innerText = "❌ Location error: " + err.message;
                    window.parent.postMessage({type: "streamlit:setComponentValue", value: null}, "*");
                },
                { enableHighAccuracy: true, timeout: 10000 }
            );
        } else {
            document.getElementById("status").innerText = "❌ Geolocation not supported by this browser.";
        }
        </script>
    """
    return components.html(location_html, height=50)


def show():
    st.title("📱 Student Attendance Scanner")

    # ── Location ──
    st.subheader("📍 Your Location")

    if "location" not in st.session_state:
        st.session_state.location = None

    loc = get_location()

    # loc comes back as a dict from the JS postMessage
    if loc and isinstance(loc, dict) and loc.get("latitude") is not None:
        st.session_state.location = loc
        lat = loc["latitude"]
        lon = loc["longitude"]
        accuracy = loc.get("accuracy", "?")
        col1, col2, col3 = st.columns(3)
        col1.metric("Latitude", f"{lat:.6f}")
        col2.metric("Longitude", f"{lon:.6f}")
        col3.metric("Accuracy", f"{float(accuracy):.0f}m")
        st.map({"lat": [lat], "lon": [lon]})
    else:
        st.warning("⏳ Waiting for location... Allow browser location permission.")

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