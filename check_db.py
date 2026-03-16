import sqlite3
import os

# Connect to the database file
DB_PATH = "synergy.db"

if not os.path.exists(DB_PATH):
    print(f"Error: {DB_PATH} not found. Have you made a booking yet?")
else:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM bookings ORDER BY id DESC")

    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} Bookings in Synergy RK:\n" + "=" * 50)

    for row in rows:
        print(f"ID: {row['id']} | Name: {row['customer_name']} | Tracking: {row['tracking_code']}")
        print(f"   Email: {row['customer_email']} | Phone: {row['customer_phone']}")
        print(f"   Details: {row['booking_details']}")
        print(f"   Total: {row['total_price']} | Payment Method: {row['payment_method']} | Status: {row['status']}")
        print("-" * 50)

    conn.close()
