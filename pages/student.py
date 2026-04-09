import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner
from utils import verify_qr_token
from database import get_connection
from datetime import datetime
import streamlit.components.v1 as components


def haversine_js():
    """Returns a JS haversine function string to embed in HTML."""
    return """
    function haversine(lat1, lon1, lat2, lon2) {
        const R = 6371000;
        const toRad = x => x * Math.PI / 180;
        const dLat = toRad(lat2 - lat1);
        const dLon = toRad(lon2 - lon1);
        const a = Math.sin(dLat/2)**2 +
                  Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon/2)**2;
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }
    """


def location_geofence_component(class_lat, class_lon, radius):
    """Renders location status and sets a hidden input to 'ALLOWED' or 'BLOCKED'."""
    components.html(f"""
        <div id="status" style="font-family:sans-serif; font-size:15px; padding:6px;">
            ⏳ Checking your location...
        </div>
        <script>
        {haversine_js()}

        const CLASS_LAT = {class_lat};
        const CLASS_LON = {class_lon};
        const RADIUS    = {radius};

        function updateBridge(value) {{
            // Write ALLOWED or BLOCKED into the hidden Streamlit text input
            const inputs = window.parent.document.querySelectorAll('input[type="text"]');
            for (let inp of inputs) {{
                if (inp.getAttribute("aria-label") === "geo_bridge") {{
                    const setter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    setter.call(inp, value);
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    break;
                }}
            }}
        }}

        if (navigator.geolocation) {{
            navigator.geolocation.getCurrentPosition(
                function(pos) {{
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    const acc = pos.coords.accuracy;
                    const dist = haversine(lat, lon, CLASS_LAT, CLASS_LON);

                    const locText = "📍 Lat: <b>" + lat.toFixed(6) + "</b> | Lon: <b>" + 
                                    lon.toFixed(6) + "</b> | Accuracy: <b>" + acc.toFixed(0) + "m</b><br>";

                    if (dist <= RADIUS) {{
                        document.getElementById("status").innerHTML =
                            locText + "✅ You are <b>" + dist.toFixed(0) + "m</b> from class — within range!";
                        updateBridge("ALLOWED:" + lat + "," + lon + "," + acc + "," + dist.toFixed(0));
                    }} else {{
                        document.getElementById("status").innerHTML =
                            locText + "🚫 You are <b>" + dist.toFixed(0) + "m</b> away — too far from class (max: {radius}m).";
                        updateBridge("BLOCKED:" + dist.toFixed(0));
                    }}
                }},
                function(err) {{
                    document.getElementById("status").innerText = "❌ Location error: " + err.message;
                    updateBridge("ERROR");
                }},
                {{ enableHighAccuracy: true, timeout: 15000 }}
            );
        }} else {{
            document.getElementById("status").innerText = "❌ Geolocation not supported.";
            updateBridge("ERROR");
        }}
        </script>
    """, height=60)


def show():
    st.title("📱 Student Attendance Scanner")

    # ── Fetch active session & classroom coordinates ──
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, course_code, lat, lon, radius FROM sessions ORDER BY id DESC LIMIT 1")
    session_row = c.fetchone()
    conn.close()

    if not session_row:
        st.warning("⚠️ No active session found. Ask your lecturer to start one.")
        return

    session_id, course_code, class_lat, class_lon, radius = session_row
    st.info(f"📚 Active Session: **{course_code}** (Session #{session_id})")

    # ── Location + Geofence check ──
    st.subheader("📍 Your Location")
    location_geofence_component(class_lat, class_lon, radius)

    # Hidden bridge — JS writes ALLOWED/BLOCKED here
    geo_status = st.text_input("geo_bridge", label_visibility="collapsed", key="geo_bridge")

    st.divider()

    # ── Scanner — only show if within range ──
    if geo_status.startswith("ALLOWED"):
        st.subheader("✅ Scan the Projected QR Code")
        qr_data = qrcode_scanner(key="scanner")

        if qr_data:
            st.info("🔍 QR scanned. Processing...")

            token = qr_data.strip()
            payload = verify_qr_token(token)

            if not payload:
                st.error("❌ QR code is expired or invalid. Ask the lecturer to refresh it.")
                return

            if payload["session_id"] != session_id:
                st.error("❌ QR does not match the active session.")
                return

            conn = get_connection()
            c = conn.cursor()
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

    elif geo_status.startswith("BLOCKED"):
        distance = geo_status.split(":")[1]
        st.error(f"🚫 Scanner disabled — you are **{distance}m** away from the classroom (max: {radius:.0f}m). You must be physically present to mark attendance.")

    elif geo_status == "ERROR":
        st.error("❌ Could not get your location. Please allow location permission and refresh.")

    else:
        st.info("⏳ Waiting for location check before enabling scanner...")