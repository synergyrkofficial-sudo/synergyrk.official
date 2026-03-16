from __future__ import annotations
import os
import sqlite3
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes to prevent "Backend Offline" browser blocks
CORS(app, resources={r"/api/*": {"origins": "*"}})

DB_PATH = "synergy.db"
DEFAULT_COUNTRY_CODE = os.getenv('DEFAULT_COUNTRY_CODE', '91')

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _ensure_schema():
    """Initializes the database and ensures all columns exist for deployment."""
    try:
        with _get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracking_code TEXT UNIQUE,
                    customer_name TEXT,
                    customer_email TEXT,
                    customer_phone TEXT,
                    booking_details TEXT,
                    total_price REAL,
                    payment_method TEXT,
                    status TEXT DEFAULT 'Pending',
                    created_at TEXT
                )
            """)
            cursor = conn.execute("PRAGMA table_info(bookings)")
            columns = {row['name'] for row in cursor.fetchall()}
            if 'total_price' not in columns:
                conn.execute("ALTER TABLE bookings ADD COLUMN total_price REAL")
            if 'payment_method' not in columns:
                conn.execute("ALTER TABLE bookings ADD COLUMN payment_method TEXT")
            conn.commit()
        print("✅ Database schema verified.")
    except Exception as e:
        print(f"❌ Schema error: {e}")

_ensure_schema()

def _normalize_phone(phone: str | None) -> str | None:
    if not phone: return None
    cleaned = ''.join(ch for ch in str(phone).strip() if ch.isdigit() or ch == '+')
    if cleaned.startswith('+'): return cleaned
    digits = ''.join(ch for ch in cleaned if ch.isdigit())
    if len(digits) == 10: return f"+{DEFAULT_COUNTRY_CODE}{digits}"
    return f"+{digits}"

def _send_email(subject: str, body: str, recipient: str) -> bool:
    try:
        smtp_user = os.getenv('SMTP_USER')
        smtp_pass = os.getenv('SMTP_PASS')
        if not smtp_user or not smtp_pass: return False
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = os.getenv('SMTP_FROM', smtp_user)
        msg['To'] = recipient
        
        with smtplib.SMTP_SSL(os.getenv('SMTP_HOST', 'smtp.gmail.com'), 465) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def _send_whatsapp(message: str, phone: str):
    try:
        sid = os.getenv('TWILIO_ACCOUNT_SID')
        token = os.getenv('TWILIO_AUTH_TOKEN')
        from_n = os.getenv('TWILIO_WHATSAPP_FROM')
        if not all([sid, token, from_n]): return
        
        client = Client(sid, token)
        client.messages.create(
            body=message,
            from_=f"whatsapp:{from_n}",
            to=f"whatsapp:{phone}"
        )
        print(f"✅ WhatsApp sent to {phone}")
    except Exception as e:
        print(f"❌ WhatsApp error: {e}")

@app.route('/api/stats', methods=['GET'])
def get_status():
    return jsonify({"status": "online"}), 200

@app.route('/api/book', methods=['POST'])
def create_booking():
    data = request.json or {}
    tracking = "SRK-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    normalized_phone = _normalize_phone(data.get('phone'))
    total = data.get('total')
    name = data.get('name')
    
    # 📝 Professional Message with Signature - STICKLY USD ($)
    detailed_msg = f"""
🌟 Thank you for choosing Synergy RK! 🌟

Your booking has been received and is currently being processed.

--- 📋 BOOKING SUMMARY ---
🎫 Tracking ID: {tracking}
👤 Client Name: {name}
🛠️ Service: {data.get('details')}
💰 Total Amount: ${total} (USD)
⏳ Payment Status: PENDING

--- 💳 PAYMENT INSTRUCTIONS ---
Please complete the payment via our global payment gateway to confirm your project:
📍 PayPal / International Transfer: synergyrk.official@gmail.com
🔗 Payment Link: https://paypal.me/synergyrk/{total}

(Note: All transactions are processed in USD. Please ensure the final amount sent is ${total})

Once paid, you can track your status on our website using your email.

---
Best Regards,

Synergy RK | Digital Solutions
🚀 Your Vision. Our Expertise.
📧 synergyrk.official@gmail.com
🌐 www.synergyrk.com
"""

    try:
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO bookings (tracking_code, customer_name, customer_email, customer_phone, booking_details, total_price, payment_method, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (tracking, name, data.get('email'), normalized_phone, data.get('details'), total, data.get('paymentMethod'), datetime.now(timezone.utc).isoformat()))
        
        _send_email(f"Booking Confirmation: {tracking}", detailed_msg, data.get('email'))
        if normalized_phone:
            _send_whatsapp(detailed_msg, normalized_phone)

        return jsonify({"success": True, "tracking_code": tracking}), 201
    except Exception as e:
        print(f"❌ Booking Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/track', methods=['GET'])
def track_booking():
    email = request.args.get('email')
    if not email: return jsonify({"ok": False, "error": "Email required"}), 400

    try:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM bookings WHERE customer_email = ? ORDER BY id DESC", (email,)).fetchall()
        
        bookings = [{
            "tracking_code": r["tracking_code"],
            "services": r["booking_details"],
            "total_price": f"${r['total_price']}",
            "payment_status": r["status"],
            "created_at": r["created_at"]
        } for r in rows]
        
        return jsonify({"ok": True, "bookings": bookings})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)