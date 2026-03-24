import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner
from utils import verify_qr_token
from database import get_connection
from datetime import datetime
import streamlit.components.v1 as components
import json


def show():
    st.title("📱 Student Attendance Scanner")

    # ── Location via JS → hidden text input bridge ──
    st.subheader("📍 Your Location")

    # JS injects coordinates into a hidden Streamlit text input
    components.html("""
        <script>
        function sendLocation() {
            if (!navigator.geolocation) {
                setInput("ERROR: Geolocation not supported");
                return;
            }
            navigator.geolocation.getCurrentPosition(
                function(pos) {
                    const val = pos.coords.latitude + "," + pos.coords.longitude + "," + pos.coords.accuracy;
                    // Find the hidden text input in the parent frame and set its value
                    const inputs = window.parent.document.querySelectorAll('input[type="text"]');
                    for (let inp of inputs) {
                        if (inp.getAttribute("aria-label") === "location_bridge") {
                            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                                window.HTMLInputElement.prototype, 'value').set;
                            nativeInputValueSetter.call(inp, val);
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            break;
                        }
                    }
                },
                function(err) { console.log("Geo error:", err.message); },
                { enableHighAccuracy: true, timeout: 15000 }
            );
        }
        sendLocation();
        </script>
    """, height=0)

    # Hidden bridge input — JS writes into this, Python reads it
    raw = st.text_input("location_bridge", label_visibility="collapsed", key="location_bridge")

    if raw and "," in raw and not raw.startswith("ERROR"):
        parts = raw.split(",")
        try:
            lat = float(parts[0])
            lon = float(parts[1])
            accuracy = float(parts[2])
            st.success(f"✅ Location acquired!")
            col1, col2, col3 = st.columns(3)
            col1.metric("Latitude", f"{lat:.6f}")
            col2.metric("Longitude", f"{lon:.6f}")
            col3.metric("Accuracy", f"{accuracy:.0f}m")
            st.map({"lat": [lat], "lon": [lon]})
        except ValueError:
            st.warning("⏳ Waiting for location...")
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