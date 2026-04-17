from app import app, get_db_connection

with app.app_context():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if columns exist first conceptually or just run ALTER IGNORE equivalents
            # In MySQL, we can't easily IF NOT EXISTS for columns in ALTER TABLE, so we just run it
            # and catch the DuplicateColumn exception if it happens.
            try:
                cursor.execute("""
                    ALTER TABLE shipments 
                    ADD COLUMN carrier VARCHAR(50) DEFAULT 'FedEx',
                    ADD COLUMN transport_mode VARCHAR(50) DEFAULT 'Road',
                    ADD COLUMN weight_kg DECIMAL(8,2) DEFAULT 100.00,
                    ADD COLUMN weather_condition VARCHAR(50) DEFAULT 'Clear',
                    ADD COLUMN priority VARCHAR(50) DEFAULT 'Standard'
                """)
                conn.commit()
                print("SUCCESS: Columns added.")
            except Exception as e:
                if 'Duplicate column name' in str(e):
                    print("Columns already exist, skipping alter.")
                else:
                    raise e
    except Exception as e:
        print(f"FAILED: {e}")
