import pymysql
import pandas as pd
import os
from datetime import datetime

def get_db_connection(config_dict):
    return pymysql.connect(
        host=config_dict.get('MYSQL_HOST', 'localhost'),
        user=config_dict.get('MYSQL_USER', 'root'),
        password=config_dict.get('MYSQL_PASSWORD', ''),
        db=config_dict.get('MYSQL_DB', 'logistics_db')
    )

def process_analytics(config_dict):
    conn = get_db_connection(config_dict)

    try:
        # ✅ STEP 1: Fetch data CORRECTLY using cursor (NOT read_sql)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM shipments")
        result = cursor.fetchall()

        # 🔥 THIS IS MAIN FIX
        df = pd.DataFrame(result)

        print("Fetched rows:", len(df))
        print(df.head())

        if df.empty:
            return "No data found in DB."

        # ✅ STEP 2: Convert dates safely
        df['expected_date'] = pd.to_datetime(df.get('expected_date'), errors='coerce')
        df['delivery_date'] = pd.to_datetime(df.get('delivery_date'), errors='coerce')
        df['dispatch_date'] = pd.to_datetime(df.get('dispatch_date'), errors='coerce')

        # ✅ STEP 3: Delay Logic
        current_date = datetime.now().date()
        updates_needed = []

        for i, row in df.iterrows():
            status = row.get('status')
            expected = row.get('expected_date')
            delivery = row.get('delivery_date')

            if status not in ['Delivered', 'Delayed']:

                if pd.notna(delivery) and pd.notna(expected):
                    if delivery.date() > expected.date():
                        df.at[i, 'status'] = 'Delayed'
                        updates_needed.append((row['id'], 'Delayed'))

                elif pd.isna(delivery) and pd.notna(expected):
                    if current_date > expected.date():
                        df.at[i, 'status'] = 'Delayed'
                        updates_needed.append((row['id'], 'Delayed'))

        # ✅ STEP 4: Update DB
        if updates_needed:
            update_cursor = conn.cursor()
            for item in updates_needed:
                update_cursor.execute(
                    "UPDATE shipments SET status=%s WHERE id=%s",
                    (item[1], item[0])
                )
            conn.commit()

        # ✅ STEP 5: Create Route like UI
        df['Route'] = df['origin'].astype(str) + " → " + df['destination'].astype(str)

        # ✅ STEP 6: Remove ONLY invalid rows (SAFE)
        df = df[df['shipment_id'].notna()]
        df = df.drop_duplicates()

        # ✅ STEP 7: Select columns
        export_df = df[[
            'shipment_id', 'Route', 'origin', 'destination', 'status',
            'cost', 'carrier', 'transport_mode', 'weight_kg',
            'weather_condition', 'priority',
            'carbon_emissions_kg', 'risk_score',
            'dispatch_date', 'expected_date', 'delivery_date'
        ]]

        export_df = export_df.reset_index(drop=True)

        print("Final rows:", len(export_df))
        print(export_df.head())

        # ✅ STEP 8: Export CSV (Power BI friendly)
        os.makedirs('exports', exist_ok=True)
        csv_path = 'exports/shipment_data.csv'

        export_df.to_csv(csv_path, index=False, encoding='utf-8-sig')

        return csv_path

    except Exception as e:
        return f"Error generating CSV: {str(e)}"

    finally:
        conn.close()