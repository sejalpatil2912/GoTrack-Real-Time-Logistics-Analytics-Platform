import os
import pymysql
import pymysql.cursors
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from services.analytics import process_analytics

app = Flask(__name__)
app.config.from_object(Config)

def get_db_connection():
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB'],
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/track', methods=['POST'])
def track_shipment():
    shipment_id = request.form.get('shipment_id')
    
    if not shipment_id:
        flash("Please enter a valid Tracking ID", "error")
        return redirect(url_for('index'))
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM shipments WHERE shipment_id = %s", (shipment_id,))
            shipment = cursor.fetchone()
            
        if shipment:
            return render_template('index.html', tracking_result=shipment)
        else:
            flash(f"Shipment {shipment_id} not found.", "error")
            return redirect(url_for('index'))
    except Exception as e:
        flash(f"Database error: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['name'] = user['name']
                
                if user['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid email or password', 'error')
        except Exception as e:
            flash(f"Database error: {str(e)}", "error")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('Email address already exists', 'error')
                    return redirect(url_for('signup'))
                    
                cursor.execute(
                    "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'user')",
                    (name, email, hashed_password)
                )
                conn.commit()
            flash('Account created successfully. Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Database error: {str(e)}", "error")
            
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def user_dashboard():
    if not session.get('user_id') or session.get('role') != 'user':
        return redirect(url_for('login'))
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM shipments WHERE user_id = %s ORDER BY id DESC", (session['user_id'],))
            shipments = cursor.fetchall()
            
            # KPI Calculations
            total_shipments = len(shipments)
            total_spend = sum(float(s.get('cost', 0)) for s in shipments if s.get('cost'))
            total_emissions = sum(float(s.get('carbon_emissions_kg', 0)) for s in shipments if s.get('carbon_emissions_kg'))
            active_shipments = sum(1 for s in shipments if s.get('status') in ['In Transit', 'Delayed', 'Pending'])
            
        return render_template('user_dashboard.html', 
                               shipments=shipments,
                               total_shipments=total_shipments,
                               total_spend=total_spend,
                               total_emissions=total_emissions,
                               active_shipments=active_shipments)
    except Exception as e:
        flash(f"Database error: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('user_id') or session.get('role') != 'admin':
        flash('Unauthorized Access', 'error')
        return redirect(url_for('login'))
        
    try:
        conn = get_db_connection()
        
        if request.method == 'POST':
            # Add or update shipment
            action = request.form.get('action')
            if action == 'add':
                shipment_id = request.form.get('shipment_id')
                user_email = request.form.get('user_email')
                origin = request.form.get('origin')
                destination = request.form.get('destination')
                cost = request.form.get('cost')
                dispatch_date = request.form.get('dispatch_date')
                expected_date = request.form.get('expected_date')
                
                # New Fields
                carrier = request.form.get('carrier', 'FedEx')
                transport_mode = request.form.get('transport_mode', 'Road')
                weight_kg = request.form.get('weight_kg', 100.0)
                weather_condition = request.form.get('weather_condition', 'Clear')
                priority = request.form.get('priority', 'Standard')
                
                # Smart Data Science Logic: CO2 and Risk
                try:
                    weight_float = float(weight_kg)
                except:
                    weight_float = 100.0
                
                emission_factors = {'Air': 1.25, 'Sea': 0.15, 'Road': 0.45, 'Rail': 0.25}
                base_emission = emission_factors.get(transport_mode, 0.45)
                carbon_emissions_kg = round(base_emission * weight_float * 10, 2)
                
                risk_score = 10
                if priority == 'Express': risk_score -= 5
                if weather_condition == 'Storm': risk_score += 60
                elif weather_condition == 'Snow': risk_score += 40
                elif weather_condition == 'Rain': risk_score += 20
                if transport_mode == 'Sea' and weather_condition in ['Storm']: risk_score += 20
                risk_score = max(0, min(100, int(risk_score)))
                
                # Smart Logic: Auto-calculate Status
                from datetime import datetime
                expected_date_obj = datetime.strptime(expected_date, '%Y-%m-%d').date()
                if expected_date_obj < datetime.now().date():
                    status = 'Delayed'
                else:
                    status = 'In Transit'
                
                with conn.cursor() as cursor:
                    # Find user ID by email
                    cursor.execute(
                        "SELECT id FROM users WHERE email = %s",
                        (user_email.strip(),)
                    )
                    user = cursor.fetchone()

                    if user is None:
                        # Auto-create the user if missing so we can assign the shipment
                        from werkzeug.security import generate_password_hash
                        hashed_pw = generate_password_hash('password123')
                        name_val = user_email.strip().split('@')[0]
                        cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'user')",
                                       (name_val, user_email.strip(), hashed_pw))
                        user_id = str(cursor.lastrowid) # Store as string since it was changed to varchar
                    else:
                        user_id = str(user['id'])
                    
                    cursor.execute("""
                        INSERT INTO shipments 
                        (shipment_id, user_id, user_email, origin, destination, status, cost, dispatch_date, expected_date, carrier, transport_mode, weight_kg, weather_condition, priority, carbon_emissions_kg, risk_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (shipment_id, user_id, user_email.strip(), origin, destination, status, cost, dispatch_date, expected_date, carrier, transport_mode, weight_float, weather_condition, priority, carbon_emissions_kg, risk_score))
                conn.commit()
                flash('Shipment added successfully', 'success')
            
            elif action == 'mark_delivered':
                shipment_id = request.form.get('shipment_id')
                from datetime import datetime
                delivery_date = datetime.now().date()
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE shipments SET status = 'Delivered', delivery_date = %s WHERE shipment_id = %s", (delivery_date, shipment_id))
                conn.commit()
                flash(f'Shipment {shipment_id} marked as Delivered!', 'success')
                
            elif action == 'delete':
                shipment_id = request.form.get('shipment_id')
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM shipments WHERE shipment_id = %s", (shipment_id,))
                conn.commit()
                flash(f'Shipment {shipment_id} deleted successfully.', 'success')
                
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM shipments ORDER BY id DESC")
            shipments = cursor.fetchall()
            
        return render_template('admin_dashboard.html', shipments=shipments)
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/admin/export_csv')
def export_csv():
    if not session.get('user_id') or session.get('role') != 'admin':
        flash('Unauthorized Access', 'error')
        return redirect(url_for('login'))

    try:
        # We process analytics which evaluates delays, generates the CSV, and updates the DB if needed
        csv_path = process_analytics(app.config)
        flash('Analytics processed and CSV exported to exports/shipment_data.csv', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f"Error generating CSV: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    # Ensure export directory exists
    os.makedirs('exports', exist_ok=True)
    app.run(debug=True, port=5000)
