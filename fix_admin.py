from app import app, get_db_connection
from werkzeug.security import generate_password_hash

with app.app_context():
    # We will set the password to 'admin123'
    hashed_pw = generate_password_hash('admin123')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if admin exists
            cursor.execute("SELECT id FROM users WHERE email='admin@gocomet.com'")
            res = cursor.fetchone()
            if res:
                cursor.execute("UPDATE users SET password=%s WHERE email='admin@gocomet.com'", (hashed_pw,))
            else:
                cursor.execute("INSERT INTO users (name, email, password, role) VALUES ('Admin', 'admin@gocomet.com', %s, 'admin')", (hashed_pw,))
        conn.commit()
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")
