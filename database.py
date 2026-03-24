import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "data/attendance.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY,
                 username TEXT UNIQUE,
                 password TEXT,
                 role TEXT,  -- lecturer or student
                 full_name TEXT)''')
    
    # Courses
    c.execute('''CREATE TABLE IF NOT EXISTS courses (
                 id INTEGER PRIMARY KEY,
                 code TEXT UNIQUE,
                 name TEXT,
                 lecturer_id INTEGER)''')
    
    # Sessions (active lectures)
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                 id INTEGER PRIMARY KEY,
                 course_code TEXT,
                 lecturer_id INTEGER,
                 start_time TEXT,
                 end_time TEXT,
                 lat REAL,
                 lon REAL,
                 radius REAL)''')
    
    # Attendance
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                 id INTEGER PRIMARY KEY,
                 session_id INTEGER,
                 student_username TEXT,
                 timestamp TEXT,
                 status TEXT)''')
    
    # Enrollments
    c.execute('''CREATE TABLE IF NOT EXISTS enrollments (
                 student_username TEXT,
                 course_code TEXT,
                 PRIMARY KEY (student_username, course_code))''')
    
    # Seed demo data
    c.execute("INSERT OR IGNORE INTO users VALUES (1, 'lecturer1', 'pass123', 'lecturer', 'Dr. Adebayo')")
    c.execute("INSERT OR IGNORE INTO users VALUES (2, 'student1', 'pass123', 'student', 'John Doe')")
    c.execute("INSERT OR IGNORE INTO users VALUES (3, 'student2', 'pass123', 'student', 'Jane Smith')")
    c.execute("INSERT OR IGNORE INTO courses VALUES (1, 'CSC101', 'Introduction to Programming', 1)")
    c.execute("INSERT OR IGNORE INTO enrollments VALUES ('student1', 'CSC101')")
    c.execute("INSERT OR IGNORE INTO enrollments VALUES ('student2', 'CSC101')")
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)