from app import get_db_connection

def test():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT user_id, user_email FROM shipments")
        print("All shipments user_ids:")
        for row in cursor.fetchall():
            print(row)
        
        cursor.execute("SELECT id, email FROM users")
        print("\nAll users:")
        for row in cursor.fetchall():
            print(row)

if __name__ == "__main__":
    test()
