from app import app, get_db_connection
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def generate_enterprise_mock_data(num_records=500):
    carriers = ['FedEx', 'DHL', 'Maersk', 'UPS', 'BlueDart', 'Hapag-Lloyd', 'CMA CGM']
    weathers = ['Clear', 'Rain', 'Storm', 'Snow', 'Extreme Heat']
    priorities = ['Standard', 'Express', 'Overnight', 'Critical']
    
    # Hubs mapped to regions to simulate logical routes
    hubs = {
        'NA': ['New York', 'Los Angeles', 'Toronto', 'Chicago'],
        'EU': ['London', 'Berlin', 'Rotterdam', 'Paris'],
        'ASIA': ['Tokyo', 'Shanghai', 'Singapore', 'Mumbai', 'Dubai'],
        'OCEANIA': ['Sydney', 'Melbourne']
    }
    
    # Generate 15 Mock Clients to assign shipments to
    mock_clients = [
        ("Acme Corp", "logistics@acmecorp.com"),
        ("Globex", "supply@globex.io"),
        ("Stark Ind", "freight@stark.com"),
        ("Wayne Ent", "transit@wayne.com"),
        ("Cyberdyne", "shipping@cyberdyne.net"),
        ("Initech", "reports@initech.co"),
        ("Umbrella Corp", "biofreight@umbrella.com"),
        ("Massive Dynamic", "global@massive.com")
    ]

    with app.app_context():
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # 1. Wipe Old Data cleanly
                cursor.execute("DELETE FROM shipments")
                
                # 2. Inject Mock Users
                user_map = {}
                default_pw = generate_password_hash('password123')
                for name, email in mock_clients:
                    cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
                    user = cursor.fetchone()
                    if not user:
                        cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'user')",
                                       (name, email, default_pw))
                        user_map[email] = cursor.lastrowid
                    else:
                        user_map[email] = user['id']
                        
                # Ensure admin exists for default mapping if needed
                admin_email = 'admin@gocomet.com'
                cursor.execute("SELECT id FROM users WHERE email=%s", (admin_email,))
                admin_res = cursor.fetchone()
                admin_id = admin_res['id'] if admin_res else None
                
                # 3. Generate Massive Kaggle-grade Dataset
                for i in range(num_records):
                    client_email = random.choice(mock_clients)[1]
                    client_id = user_map[client_email]
                    
                    shipment_id = f"TRK-{random.randint(100000, 999999)}"
                    
                    # Logic: Determine origin and destination
                    orig_region = random.choice(list(hubs.keys()))
                    dest_region = random.choice(list(hubs.keys()))
                    origin = random.choice(hubs[orig_region])
                    
                    if orig_region == dest_region:
                        # Domestic or Regional
                        available_dests = [c for c in hubs[orig_region] if c != origin]
                        destination = random.choice(available_dests) if available_dests else origin + " Sub-hub"
                        mode = random.choice(['Road', 'Rail', 'Air'])
                    else:
                        # International
                        destination = random.choice(hubs[dest_region])
                        mode = random.choice(['Air', 'Sea'])
                        
                    carrier = random.choice(carriers)
                    # Adjust carriers logically based on mode
                    if mode == 'Sea': carrier = random.choice(['Maersk', 'Hapag-Lloyd', 'CMA CGM'])
                    if mode == 'Air': carrier = random.choice(['FedEx', 'DHL', 'UPS'])

                    weight = round(random.uniform(10.0, 5000.0), 1)
                    weather = random.choices(weathers, weights=[60, 20, 10, 5, 5])[0]
                    priority = random.choice(priorities)
                    
                    # Costing Logic
                    base_rate = 100
                    if mode == 'Air': base_rate = 500
                    if mode == 'Sea': base_rate = 50
                    cost = round(base_rate + (weight * random.uniform(0.1, 0.5)), 2)
                    if priority in ['Express', 'Overnight', 'Critical']: cost *= 1.5
                    
                    # Dates Logic
                    dispatch = datetime.now() - timedelta(days=random.randint(1, 90))
                    
                    # Transit time baseline
                    transit_days = 3
                    if mode == 'Sea': transit_days = random.randint(20, 45)
                    elif mode == 'Rail': transit_days = random.randint(5, 14)
                    elif mode == 'Road': transit_days = random.randint(2, 7)
                    elif mode == 'Air': transit_days = random.randint(1, 4)
                    
                    expected = dispatch + timedelta(days=transit_days)
                    
                    # Status & Delivery Logic
                    today = datetime.now().date()
                    if expected.date() < today:
                        # Should have arrived. Did weather delay it?
                        if weather in ['Storm', 'Snow'] or random.random() > 0.8:
                            status = 'Delayed'
                            delivery_date = None
                        else:
                            status = 'Delivered'
                            delivery_date = expected.date() + timedelta(days=random.randint(-1, 2))
                    else:
                        # Still active
                        status = 'In Transit'
                        delivery_date = None
                    
                    # Smart Data Science Features
                    emission_factors = {'Air': 1.25, 'Sea': 0.15, 'Road': 0.45, 'Rail': 0.25}
                    carbon_emissions_kg = round(emission_factors.get(mode, 0.45) * float(weight) * (transit_days * 10), 2)
                    
                    risk_score = 10
                    if priority in ['Express', 'Critical']: risk_score -= 5
                    if weather == 'Storm': risk_score += 65
                    elif weather == 'Snow': risk_score += 45
                    elif weather == 'Rain': risk_score += 15
                    elif weather == 'Extreme Heat': risk_score += 25
                    if mode == 'Sea' and weather in ['Storm', 'Extreme Heat']: risk_score += 25
                    risk_score = max(0, min(100, int(risk_score)))
                    
                    cursor.execute("""
                        INSERT INTO shipments 
                        (shipment_id, user_id, user_email, origin, destination, status, cost, carrier, transport_mode, weight_kg, weather_condition, priority, dispatch_date, expected_date, delivery_date, carbon_emissions_kg, risk_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (shipment_id, client_id, client_email, origin, destination, status, cost, carrier, mode, weight, weather, priority, dispatch.date(), expected.date(), delivery_date, carbon_emissions_kg, risk_score))
                
                conn.commit()
                print(f"SUCCESS: Enterprise Kaggle-grade Mock Data ({num_records} records) successfully injected!")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    generate_enterprise_mock_data(500)
