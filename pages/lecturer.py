import streamlit as st
from database import get_connection
import qrcode
from io import BytesIO
from utils import create_qr_token
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime


def show():
    st.title("👨‍🏫 Lecturer Dashboard")

    tab1, tab2, tab3 = st.tabs(["▶️ Live Session", "📊 Session Report", "📅 Semester Report"])

    # ──────────────────────────────────────────────
    # TAB 1 — Live Session (your existing code)
    # ──────────────────────────────────────────────
    with tab1:
        course = st.selectbox("Select Course", ["CSC101"], key="course_select")

        if st.button("🚀 Start New Attendance Session", type="primary"):
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "INSERT INTO sessions (course_code, lecturer_id, start_time, lat, lon, radius) VALUES (?, 1, ?, 6.5244, 3.3792, 50)",
                (course, st.session_state.username),
            )
            session_id = c.lastrowid
            conn.commit()
            conn.close()

            st.session_state.current_session_id = session_id
            st.success(f"Session {session_id} started! Project this QR code.")

        if "current_session_id" in st.session_state:
            session_id = st.session_state.current_session_id

            # Auto-refresh every 25 seconds
            st_autorefresh(interval=25000, limit=1000, key="qrrefresh")

            token = create_qr_token(session_id)
            qr = qrcode.make(token)
            buf = BytesIO()
            qr.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="PROJECT THIS QR CODE (refreshes every 25s)", width=400)

            # Live attendance list for current session
            st.subheader("👥 Students Marked Present")
            conn = get_connection()
            df_live = pd.read_sql_query(
                """SELECT u.full_name AS Student, a.student_username AS Username, a.timestamp AS Time
                   FROM attendance a
                   JOIN users u ON a.student_username = u.username
                   WHERE a.session_id=?""",
                conn,
                params=(session_id,),
            )
            conn.close()
            if df_live.empty:
                st.info("No students marked yet.")
            else:
                st.dataframe(df_live, use_container_width=True)
                st.metric("Total Present", len(df_live))

            if st.button("⏹️ End Session"):
                del st.session_state.current_session_id
                st.rerun()

    # ──────────────────────────────────────────────
    # TAB 2 — Per-Session Report
    # ──────────────────────────────────────────────
    with tab2:
        st.subheader("📊 End-of-Class Report")

        conn = get_connection()
        sessions_df = pd.read_sql_query(
            "SELECT id, course_code, start_time FROM sessions ORDER BY start_time DESC",
            conn,
        )
        conn.close()

        if sessions_df.empty:
            st.info("No sessions found yet.")
        else:
            session_labels = {
                row["id"]: f"Session {row['id']} — {row['course_code']} ({row['start_time']})"
                for _, row in sessions_df.iterrows()
            }
            selected_id = st.selectbox(
                "Choose a session",
                options=list(session_labels.keys()),
                format_func=lambda x: session_labels[x],
                key="report_session",
            )

            conn = get_connection()

            # Get the course_code for this session
            session_info = pd.read_sql_query(
                "SELECT course_code FROM sessions WHERE id=?", conn, params=(selected_id,)
            )
            session_course = session_info.iloc[0]["course_code"] if not session_info.empty else None

            # Enrolled students for that course (with full name)
            all_students = pd.read_sql_query(
                """SELECT u.username, u.full_name
                   FROM enrollments e
                   JOIN users u ON e.student_username = u.username
                   WHERE e.course_code = ?""",
                conn,
                params=(session_course,),
            )

            # Students who attended
            attended = pd.read_sql_query(
                "SELECT student_username, timestamp FROM attendance WHERE session_id=?",
                conn,
                params=(selected_id,),
            )
            conn.close()

            # Merge to get Present / Absent
            report = all_students.copy()
            report.columns = ["Username", "Student"]
            report["Status"] = report["Username"].apply(
                lambda s: "✅ Present" if s in attended["student_username"].values else "❌ Absent"
            )
            attended_map = attended.set_index("student_username")["timestamp"].to_dict()
            report["Time Marked"] = report["Username"].map(attended_map).fillna("—")
            report = report[["Student", "Username", "Status", "Time Marked"]]

            present_count = (report["Status"] == "✅ Present").sum()
            absent_count = (report["Status"] == "❌ Absent").sum()
            total = len(report)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Students", total)
            col2.metric("Present", present_count)
            col3.metric("Absent", absent_count)

            st.dataframe(report, use_container_width=True)

            # Download CSV
            csv = report.to_csv(index=False).encode()
            st.download_button(
                "⬇️ Download Session Report (CSV)",
                data=csv,
                file_name=f"session_{selected_id}_report.csv",
                mime="text/csv",
            )

    # ──────────────────────────────────────────────
    # TAB 3 — Semester / Course Summary Report
    # ──────────────────────────────────────────────
    with tab3:
        st.subheader("📅 Semester Attendance Summary")

        conn = get_connection()
        courses = pd.read_sql_query(
            "SELECT DISTINCT course_code FROM sessions", conn
        )["course_code"].tolist()
        conn.close()

        if not courses:
            st.info("No sessions recorded yet.")
        else:
            selected_course = st.selectbox("Select Course", courses, key="sem_course")

            conn = get_connection()

            # All sessions for this course
            sessions = pd.read_sql_query(
                "SELECT id, start_time FROM sessions WHERE course_code=?",
                conn,
                params=(selected_course,),
            )
            total_sessions = len(sessions)

            # Enrolled students for this course (with full name)
            all_students_df = pd.read_sql_query(
                """SELECT u.username, u.full_name
                   FROM enrollments e
                   JOIN users u ON e.student_username = u.username
                   WHERE e.course_code = ?""",
                conn,
                params=(selected_course,),
            )
            all_students = all_students_df.to_dict("records")

            # All attendance records for this course
            attendance_all = pd.read_sql_query(
                """
                SELECT a.student_username, a.session_id
                FROM attendance a
                JOIN sessions s ON a.session_id = s.id
                WHERE s.course_code = ?
                """,
                conn,
                params=(selected_course,),
            )
            conn.close()

            summary_rows = []
            for row in all_students:
                student_username = row["username"]
                student_name = row["full_name"]
                attended_count = len(
                    attendance_all[attendance_all["student_username"] == student_username]
                )
                pct = (attended_count / total_sessions * 100) if total_sessions > 0 else 0
                summary_rows.append(
                    {
                        "Student": student_name,
                        "Username": student_username,
                        "Sessions Attended": attended_count,
                        "Total Sessions": total_sessions,
                        "Attendance %": round(pct, 1),
                        "Status": "⚠️ At Risk" if pct < 75 else "✅ Good",
                    }
                )

            summary_df = pd.DataFrame(summary_rows).sort_values("Attendance %", ascending=False)

            # Summary metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Sessions", total_sessions)
            col2.metric("Total Students", len(all_students))
            at_risk = sum(1 for r in summary_rows if r["Attendance %"] < 75)
            col3.metric("⚠️ At-Risk Students (<75%)", at_risk)

            st.dataframe(summary_df, use_container_width=True)

            # Download semester CSV
            csv_sem = summary_df.to_csv(index=False).encode()
            st.download_button(
                "⬇️ Download Semester Report (CSV)",
                data=csv_sem,
                file_name=f"{selected_course}_semester_report.csv",
                mime="text/csv",
            )