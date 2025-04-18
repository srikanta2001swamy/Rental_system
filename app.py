from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, date
import os

app = Flask(__name__)

def init_db():
    db_path = os.getenv('DATABASE_PATH', 'rental.db')
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity INTEGER, rent_per_day REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS customers 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, phone_no TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS rentals 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, customer_id INTEGER, 
                     rental_date TEXT, expected_return_date TEXT, advance_paid REAL, returned INTEGER DEFAULT 0, 
                     return_date TEXT, 
                     FOREIGN KEY(item_id) REFERENCES inventory(id), 
                     FOREIGN KEY(customer_id) REFERENCES customers(id))''')
        conn.commit()

def calculate_rental_amount(rental_date, end_date, rent_per_day):
    start = datetime.strptime(rental_date, '%Y-%m-%d %H:%M:%S')
    end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.now()
    days = (end.date() - start.date()).days
    return max(days, 1) * rent_per_day  # Ensure at least 1 day for same-day rentals

@app.route('/')
def index():
    db_path = os.getenv('DATABASE_PATH', 'rental.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM inventory")
    total_inventory = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM customers")
    total_customers = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM rentals WHERE returned = 0")
    total_active_rentals = c.fetchone()[0]
    
    conn.close()
    return render_template('index.html', 
                         total_inventory=total_inventory,
                         total_customers=total_customers,
                         total_active_rentals=total_active_rentals)

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    db_path = os.getenv('DATABASE_PATH', 'rental.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        rent_per_day = request.form['rent_per_day']
        c.execute("INSERT INTO inventory (name, quantity, rent_per_day) VALUES (?, ?, ?)", 
                 (name, quantity, rent_per_day))
        conn.commit()
    
    c.execute("SELECT * FROM inventory")
    items = c.fetchall()
    conn.close()
    return render_template('inventory.html', items=items)

@app.route('/inventory/delete/<int:id>', methods=['POST'])
def delete_inventory(id):
    db_path = os.getenv('DATABASE_PATH', 'rental.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM rentals WHERE item_id = ? AND returned = 0", (id,))
    active_rentals = c.fetchone()[0]
    
    if active_rentals == 0:
        c.execute("DELETE FROM inventory WHERE id = ?", (id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('inventory'))

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    db_path = os.getenv('DATABASE_PATH', 'rental.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone_no = request.form['phone_no']
        c.execute("INSERT INTO customers (name, email, phone_no) VALUES (?, ?, ?)", 
                 (name, email, phone_no))
        conn.commit()
    
    c.execute('''SELECT c.id, c.name, c.email, c.phone_no, 
                (SELECT COUNT(*) FROM rentals r WHERE r.customer_id = c.id AND r.returned = 0) as active_rentals 
                FROM customers c''')
    customers = c.fetchall()
    conn.close()
    return render_template('customers.html', customers=customers)

@app.route('/customers/delete/<int:id>', methods=['POST'])
def delete_customer(id):
    db_path = os.getenv('DATABASE_PATH', 'rental.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM rentals WHERE customer_id = ? AND returned = 0", (id,))
    active_rentals = c.fetchone()[0]
    
    if active_rentals == 0:
        c.execute("DELETE FROM customers WHERE id = ?", (id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('customers'))

@app.route('/rentals', methods=['GET', 'POST'])
def rentals():
    db_path = os.getenv('DATABASE_PATH', 'rental.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    if request.method == 'POST':
        item_id = request.form['item_id']
        customer_id = request.form['customer_id']
        expected_return_date = request.form['expected_return_date']
        advance_paid = request.form['advance_paid']
        rental_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO rentals (item_id, customer_id, rental_date, expected_return_date, 
                    advance_paid, returned) VALUES (?, ?, ?, ?, ?, 0)''', 
                 (item_id, customer_id, rental_date, expected_return_date, advance_paid))
        c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (item_id,))
        conn.commit()
    
    c.execute('''SELECT r.id, i.name, c.name, r.rental_date, r.expected_return_date, 
                r.advance_paid, r.returned, r.return_date, i.rent_per_day 
                FROM rentals r 
                JOIN inventory i ON r.item_id = i.id 
                JOIN customers c ON r.customer_id = c.id''')
    rentals = c.fetchall()
    rentals_with_calculations = []
    for rental in rentals:
        total_amount = calculate_rental_amount(
            rental[3], 
            rental[7] if rental[6] == 1 else rental[4], 
            rental[8]
        )
        balance = total_amount - float(rental[5])
        rentals_with_calculations.append(rental + (total_amount, balance))
    
    c.execute("SELECT id, name FROM inventory WHERE quantity > 0")
    items = c.fetchall()
    c.execute("SELECT id, name FROM customers")
    customers = c.fetchall()
    conn.close()
    return render_template('rentals.html', rentals=rentals_with_calculations, items=items, customers=customers)

@app.route('/rentals/return/<int:id>', methods=['POST'])
def return_rental(id):
    db_path = os.getenv('DATABASE_PATH', 'rental.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    return_date = datetime.now().strftime('%Y-%m-%d')
    c.execute("UPDATE rentals SET returned = 1, return_date = ? WHERE id = ?", (return_date, id))
    c.execute('''UPDATE inventory SET quantity = quantity + 1 
                WHERE id = (SELECT item_id FROM rentals WHERE id = ?)''', (id,))
    conn.commit()
    
    conn.close()
    return redirect(url_for('rentals'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)

