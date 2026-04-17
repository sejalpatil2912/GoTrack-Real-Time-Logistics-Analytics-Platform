from app import app, get_db_connection

with app.app_context():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            try:
                cursor.execute("""
                    ALTER TABLE shipments 
                    ADD COLUMN carbon_emissions_kg DECIMAL(10,2) DEFAULT 0.00,
                    ADD COLUMN risk_score INT DEFAULT 0
                """)
                conn.commit()
                print("SUCCESS: Carbon & Risk columns added.")
            except Exception as e:
                if 'Duplicate column name' in str(e):
                    print("Columns already exist, skipping alter.")
                else:
                    raise e
    except Exception as e:
        print(f"FAILED: {e}")
