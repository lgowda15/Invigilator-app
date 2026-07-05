import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event, Alarm
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.encoders import encode_base64
import re
import time
import bcrypt

# ============================================================================
# CONFIG
# ============================================================================

st.set_page_config(page_title="Invigilator Signup", layout="wide")

BASKETS = {
    1: {"day": "Monday", "time": "1:15 PM - 2:00 PM", "rooms": 4, "available": 15},
    2: {"day": "Tuesday", "session": "S1", "time": "1:15 PM - 2:00 PM", "rooms": 5, "available": 8},
    3: {"day": "Tuesday", "session": "S2", "time": "3:30 PM - 4:15 PM", "rooms": 5, "available": 11},
    4: {"day": "Wednesday", "time": "1:15 PM - 2:00 PM", "rooms": 5, "available": 8},
    5: {"day": "Thursday", "time": "1:15 PM - 2:00 PM", "rooms": 5, "available": 7},
    6: {"day": "Friday", "time": "1:15 PM - 2:00 PM", "rooms": 4, "available": 11},
}

TERM_START = datetime(2026, 7, 6)
TERM_END = datetime(2026, 9, 11)
TIMEZONE = pytz.timezone('Asia/Kolkata')

GMAIL_ADDRESS = "likith.srinivasagowda@gmail.com"
GMAIL_PASSWORD = st.secrets.get("gmail_password", "PLACEHOLDER")

DB_URL = st.secrets.get("database_url", "")

OFFICE_USERS = {
    "likith": "$2b$12$f8wK9EqKh8JBCJjVKlDlfOXPkbEIt6CYQMF2QDL06eWE/8pcjFQtm", #Password123
    "preetha": "$2b$12$Vkcu3ZdMAqh95VNcaR0oduaDlnE4..plLavlArd3ElaEMQ59BRAcC", #AnotherPassword456
}

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

# ============================================================================
# DATABASE (PostgreSQL via Render)
# ============================================================================

def get_db_connection():
    """Get a PostgreSQL connection"""
    if not DB_URL:
        st.error("❌ Database URL not configured in secrets.toml")
        st.stop()
    
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)[:100]}")
        st.stop()

def init_db():
    """Initialize database tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'Active'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signups (
                id SERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                name TEXT NOT NULL,
                basket INTEGER NOT NULL,
                week INTEGER NOT NULL,
                status TEXT NOT NULL,
                email TEXT NOT NULL,
                calendar_sent TEXT DEFAULT 'No'
            )
        ''')
        
        conn.commit()
    except Exception as e:
        if "already exists" not in str(e).lower():
            st.error(f"Database init error: {str(e)[:100]}")
    finally:
        cursor.close()
        conn.close()

# ============================================================================
# VALIDATION & SECURITY
# ============================================================================

def validate_name(name):
    if not name or len(name) < 2 or len(name) > 100:
        return False, "Name must be 2-100 characters"
    if not re.match(r"^[a-zA-Z\s\-']+$", name):
        return False, "Name can only contain letters, spaces, hyphens, and apostrophes"
    return True, ""

def validate_email(email):
    if not email or len(email) > 254:
        return False, "Invalid email"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, ""

def sanitize_input(user_input):
    if not isinstance(user_input, str):
        return ""
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', user_input)
    return sanitized[:255]

# ============================================================================
# STUDENT AUTHENTICATION
# ============================================================================

def register_student(email, name, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT email FROM accounts WHERE email = %s", (email,))
        if cursor.fetchone():
            conn.close()
            return False, "Email already registered"
        
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        cursor.execute('''
            INSERT INTO accounts (email, name, password_hash, created_at, status)
            VALUES (%s, %s, %s, %s, %s)
        ''', (email, name, hashed_password, datetime.now(TIMEZONE).isoformat(), "Active"))
        
        conn.commit()
        conn.close()
        return True, "Account created successfully"
    
    except Exception as e:
        conn.close()
        return False, f"Error: {str(e)[:100]}"

def verify_student_login(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name, password_hash FROM accounts WHERE email = %s", (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            name, hashed = row[0], row[1]
            if bcrypt.checkpw(password.encode(), hashed.encode()):
                return True, name
        
        return False, None
    
    except Exception:
        conn.close()
        return False, None

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_current_week():
    today = datetime.now(TIMEZONE).date()
    if today < TERM_START.date():
        return 1
    if today > TERM_END.date():
        return 10
    weeks_elapsed = (today - TERM_START.date()).days // 7
    return min(weeks_elapsed + 1, 10)

def get_week_dates(week_num):
    week_start = TERM_START + timedelta(weeks=week_num - 1)
    week_end = week_start + timedelta(days=6)
    return week_start.date(), week_end.date()

def get_basket_display_name(basket_num):
    b = BASKETS[basket_num]
    if "session" in b:
        return f"Basket {basket_num} - {b['day']} {b['session']} ({b['time']})"
    else:
        return f"Basket {basket_num} - {b['day']} ({b['time']})"

def get_session_time(basket_num, week_num):
    b = BASKETS[basket_num]
    week_start, _ = get_week_dates(week_num)
    
    day_name = b["day"].lower()
    day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4}
    target_day = day_map[day_name]
    
    current = week_start
    while current.weekday() != target_day:
        current += timedelta(days=1)
    
    time_str = b["time"].split(" - ")[0]
    hour, minute = map(int, time_str.replace(" PM", "").replace(" AM", "").split(":"))
    if "PM" in b["time"] and hour != 12:
        hour += 12
    
    return TIMEZONE.localize(datetime.combine(current, datetime.min.time().replace(hour=hour, minute=minute)))

def check_cancellation_window(basket_num, week_num):
    session_time = get_session_time(basket_num, week_num)
    current_time = TIMEZONE.localize(datetime.now())
    time_remaining_hours = (session_time - current_time).total_seconds() / 3600
    return time_remaining_hours > 3

def get_student_signups(email, week_num=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if week_num:
            cursor.execute("SELECT * FROM signups WHERE email = %s AND week = %s", (email, week_num))
        else:
            cursor.execute("SELECT * FROM signups WHERE email = %s", (email,))
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    except Exception:
        conn.close()
        return []

def get_basket_signup_counts(basket_num, week_num):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT status, COUNT(*) as count FROM signups 
            WHERE basket = %s AND week = %s 
            GROUP BY status
        ''', (basket_num, week_num))
        
        counts = {"Primary": 0, "Backup": 0}
        for row in cursor.fetchall():
            counts[row[0]] = row[1]
        
        conn.close()
        return counts
    
    except Exception:
        conn.close()
        return {"Primary": 0, "Backup": 0}

def add_signup(name, basket_num, week_num, status, email):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO signups (timestamp, name, basket, week, status, email, calendar_sent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (datetime.now(TIMEZONE).isoformat(), name, basket_num, week_num, status, email, "No"))
        
        signup_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return signup_id
    
    except Exception:
        conn.close()
        return None

def mark_calendar_sent(signup_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE signups SET calendar_sent = 'Yes' WHERE id = %s", (signup_id,))
        conn.commit()
        conn.close()
    except Exception:
        conn.close()

def delete_signup(email, basket_num, week_num):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM signups WHERE email = %s AND basket = %s AND week = %s
        ''', (email, basket_num, week_num))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def get_all_signups():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM signups ORDER BY timestamp DESC")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    except Exception:
        conn.close()
        return []

def generate_ics_file(basket_num, week_num, student_name, is_backup=False):
    session_time = get_session_time(basket_num, week_num)
    event_end = session_time + timedelta(minutes=45)
    
    cal = Calendar()
    cal.add('prodid', '-//Invigilator Signup//EN')
    cal.add('version', '2.0')
    
    event = Event()
    event.add('summary', f"Invigilate - Basket {basket_num}")
    event.add('description', f"Case Study Writing Invigilation - Basket {basket_num}\n{'[BACKUP]' if is_backup else ''}")
    event.add('dtstart', session_time)
    event.add('dtend', event_end)
    event.add('dtstamp', TIMEZONE.localize(datetime.now()))
    
    if not is_backup:
        alarm = Alarm()
        alarm.add('action', 'DISPLAY')
        alarm.add('trigger', timedelta(minutes=-15))
        alarm.add('description', 'Invigilator Reminder')
        event.add_component(alarm)
    
    cal.add_component(event)
    return cal.to_ical()

def send_calendar_invite(recipient_email, basket_num, week_num, student_name, is_backup=False):
    if GMAIL_PASSWORD == "PLACEHOLDER":
        return False
    
    try:
        ics_content = generate_ics_file(basket_num, week_num, student_name, is_backup)
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = f"Invigilator Assignment - Basket {basket_num} - Week {week_num}"
        
        body = f"""Hi {student_name},

You have been assigned as {'BACKUP ' if is_backup else ''}invigilator for Basket {basket_num} (Week {week_num}).

Details:
- {get_basket_display_name(basket_num)}
- Week: {week_num}

Please add the attached calendar invite to your calendar.

{'NOTE: You are a BACKUP. You will be contacted 24 hours before if needed.' if is_backup else 'See you at the office!'}

Best regards,
Invigilator Coordination
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(ics_content)
        encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="basket_{basket_num}_week_{week_num}.ics"')
        msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception:
        return False

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    init_db()
    
    st.title("📋 Case Study Invigilator Signup System")
    
    if "student_authenticated" not in st.session_state:
        st.session_state.student_authenticated = False
    if "student_email" not in st.session_state:
        st.session_state.student_email = None
    if "student_name" not in st.session_state:
        st.session_state.student_name = None
    if "office_authenticated" not in st.session_state:
        st.session_state.office_authenticated = False
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
    if "lockout_time" not in st.session_state:
        st.session_state.lockout_time = None
    
    with st.sidebar:
        st.header("🎓 Student Portal")
        
        if not st.session_state.student_authenticated:
            auth_choice = st.radio("", ["Login", "Register"], label_visibility="collapsed")
            
            if auth_choice == "Login":
                with st.form("student_login"):
                    email = st.text_input("Email", max_chars=254)
                    password = st.text_input("Password", type="password", max_chars=128)
                    login_btn = st.form_submit_button("Login", use_container_width=True)
                
                if login_btn:
                    email = sanitize_input(email)
                    if not email or not password:
                        st.error("❌ Email and password required")
                    else:
                        verified, name = verify_student_login(email, password)
                        if verified:
                            st.session_state.student_authenticated = True
                            st.session_state.student_email = email
                            st.session_state.student_name = name
                            st.success(f"✅ Welcome, {name}!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid credentials")
            
            else:
                with st.form("student_register"):
                    reg_name = st.text_input("Full Name", max_chars=100)
                    reg_email = st.text_input("Email", max_chars=254)
                    reg_password = st.text_input("Password (min 8)", type="password", max_chars=128)
                    reg_confirm = st.text_input("Confirm Password", type="password", max_chars=128)
                    register_btn = st.form_submit_button("Create Account", use_container_width=True)
                
                if register_btn:
                    name_valid, name_error = validate_name(reg_name)
                    email_valid, email_error = validate_email(reg_email)
                    
                    if not name_valid:
                        st.error(f"❌ {name_error}")
                    elif not email_valid:
                        st.error(f"❌ {email_error}")
                    elif len(reg_password) < 8:
                        st.error("❌ Min 8 characters")
                    elif reg_password != reg_confirm:
                        st.error("❌ Passwords don't match")
                    else:
                        success, message = register_student(reg_email, reg_name, reg_password)
                        if success:
                            st.success(message)
                        else:
                            st.error(f"❌ {message}")
        else:
            st.write(f"**{st.session_state.student_name}**")
            st.write(f"📧 {st.session_state.student_email}")
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.student_authenticated = False
                st.rerun()
    
    if not st.session_state.student_authenticated:
        st.info("👈 Login or register in the sidebar")
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["📝 Sign Up", "📊 My Dashboard", "🔧 Office"])
    
    with tab1:
        st.header("Sign Up for Invigilator Slots")
        
        current_week = get_current_week()
        week_start, week_end = get_week_dates(current_week)
        st.info(f"**Week {current_week}** ({week_start} to {week_end})")
        
        st.subheader("Current Availability")
        cols = st.columns(3)
        for idx, basket_num in enumerate(range(1, 7)):
            counts = get_basket_signup_counts(basket_num, current_week)
            rooms = BASKETS[basket_num]["rooms"]
            with cols[idx % 3]:
                st.metric(
                    f"Basket {basket_num}",
                    f"{counts['Primary']}/{rooms} Primary",
                    f"{counts['Backup']}/2 Backup"
                )
        
        st.divider()
        
        with st.form("signup_form"):
            st.subheader("Select Baskets")
            selected = []
            for basket_num in range(1, 7):
                if st.checkbox(get_basket_display_name(basket_num), key=f"bask_{basket_num}"):
                    selected.append(basket_num)
            
            submitted = st.form_submit_button("Submit", type="primary")
        
        if submitted:
            if not selected:
                st.error("❌ Select at least one basket")
            else:
                count = 0
                for basket_num in selected:
                    counts = get_basket_signup_counts(basket_num, current_week)
                    rooms = BASKETS[basket_num]["rooms"]
                    
                    if counts["Primary"] < rooms:
                        status = "Primary"
                    elif counts["Backup"] < 2:
                        status = "Backup"
                    else:
                        st.warning(f"Basket {basket_num} full")
                        continue
                    
                    signup_id = add_signup(
                        st.session_state.student_name,
                        basket_num,
                        current_week,
                        status,
                        st.session_state.student_email
                    )
                    
                    if signup_id:
                        count += 1
                        sent = send_calendar_invite(
                            st.session_state.student_email,
                            basket_num,
                            current_week,
                            st.session_state.student_name,
                            status == "Backup"
                        )
                        if sent:
                            mark_calendar_sent(signup_id)
                
                if count > 0:
                    st.success(f"✅ Signed up for {count} basket(s)!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
    
    with tab2:
        st.header("My Dashboard")
        
        signups = get_student_signups(st.session_state.student_email)
        
        if not signups:
            st.info("No signups yet")
        else:
            by_week = {}
            for signup in signups:
                week = signup["week"]
                if week not in by_week:
                    by_week[week] = []
                by_week[week].append(signup)
            
            for week_num in sorted(by_week.keys()):
                week_signups = by_week[week_num]
                week_start, week_end = get_week_dates(week_num)
                
                with st.expander(f"Week {week_num} ({week_start} - {week_end})", expanded=(week_num == get_current_week())):
                    for signup in week_signups:
                        basket_num = signup["basket"]
                        status = signup["status"]
                        
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.write(f"**{get_basket_display_name(basket_num)}**")
                        with col2:
                            st.write(f"*{status}*")
                        with col3:
                            if check_cancellation_window(basket_num, week_num):
                                if st.button("❌ Cancel", key=f"cancel_{basket_num}_{week_num}"):
                                    if delete_signup(st.session_state.student_email, basket_num, week_num):
                                        st.success("✅ Cancelled")
                                        time.sleep(1)
                                        st.rerun()
                            else:
                                st.write("⏳ Too late")
    
    with tab3:
        st.header("Office Dashboard")
        
        if not st.session_state.office_authenticated:
            if st.session_state.lockout_time:
                time_remaining = LOGIN_LOCKOUT_MINUTES * 60 - (time.time() - st.session_state.lockout_time)
                if time_remaining > 0:
                    st.error(f"🔒 Locked out. Try in {int(time_remaining / 60)} min")
                    st.stop()
                else:
                    st.session_state.lockout_time = None
                    st.session_state.login_attempts = 0
            
            with st.form("office_login"):
                username = st.text_input("Username", max_chars=50)
                password = st.text_input("Password", type="password", max_chars=128)
                btn = st.form_submit_button("Login")
            
            if btn:
                if username in OFFICE_USERS:
                    try:
                        if bcrypt.checkpw(password.encode(), OFFICE_USERS[username].encode()):
                            st.session_state.office_authenticated = True
                            st.session_state.login_attempts = 0
                            st.rerun()
                    except:
                        pass
                
                st.session_state.login_attempts += 1
                remaining = MAX_LOGIN_ATTEMPTS - st.session_state.login_attempts
                
                if st.session_state.login_attempts >= MAX_LOGIN_ATTEMPTS:
                    st.session_state.lockout_time = time.time()
                    st.error(f"🔒 Locked")
                else:
                    st.error(f"❌ Invalid. {remaining} left")
        else:
            if st.button("🚪 Logout"):
                st.session_state.office_authenticated = False
                st.rerun()
            
            all_signups = get_all_signups()
            
            if all_signups:
                df = pd.DataFrame(all_signups)
                df = df[["timestamp", "name", "basket", "week", "status", "email", "calendar_sent"]]
                df.columns = ["Timestamp", "Name", "Basket", "Week", "Status", "Email", "Calendar_Sent"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    filter_week = st.multiselect("Week", sorted(df["Week"].unique()))
                with col2:
                    filter_basket = st.multiselect("Basket", sorted(df["Basket"].unique()))
                with col3:
                    filter_status = st.multiselect("Status", ["Primary", "Backup"], default=["Primary", "Backup"])
                
                filtered = df.copy()
                if filter_week:
                    filtered = filtered[filtered["Week"].isin(filter_week)]
                if filter_basket:
                    filtered = filtered[filtered["Basket"].isin(filter_basket)]
                filtered = filtered[filtered["Status"].isin(filter_status)]
                
                st.dataframe(filtered, use_container_width=True)
                
                csv = filtered.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    csv,
                    f"signups_{datetime.now(TIMEZONE).strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv"
                )
            else:
                st.info("No signups yet")

if __name__ == "__main__":
    main()