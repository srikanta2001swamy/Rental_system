from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

def init_db():
    with sqlite3.connect('rental.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS customers 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS rentals 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, customer_id INTEGER, 
                     rental_date TEXT, FOREIGN KEY(item_id) REFERENCES inventory(id), 
                     FOREIGN KEY(customer_id) REFERENCES customers(id))''')
        conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    conn = sqlite3.connect('rental.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        c.execute("INSERT INTO inventory (name, quantity) VALUES (?, ?)", (name, quantity))
        conn.commit()
    
    c.execute("SELECT * FROM inventory")
    items = c.fetchall()
    conn.close()
    return render_template('inventory.html', items=items)

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    conn = sqlite3.connect('rental.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        c.execute("INSERT INTO customers (name, email) VALUES (?, ?)", (name, email))
        conn.commit()
    
    c.execute("SELECT * FROM customers")
    customers = c.fetchall()
    conn.close()
    return render_template('customers.html', customers=customers)

@app.route('/rentals', methods=['GET', 'POST'])
def rentals():
    conn = sqlite3.connect('rental.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        item_id = request.form['item_id']
        customer_id = request.form['customer_id']
        rental_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO rentals (item_id, customer_id, rental_date) VALUES (?, ?, ?)", 
                 (item_id, customer_id, rental_date))
        c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (item_id,))
        conn.commit()
    
    c.execute('''SELECT r.id, i.name, c.name, r.rental_date 
                FROM rentals r 
                JOIN inventory i ON r.item_id = i.id 
                JOIN customers c ON r.customer_id = c.id''')
    rentals = c.fetchall()
    c.execute("SELECT id, name FROM inventory WHERE quantity > 0")
    items = c.fetchall()
    c.execute("SELECT id, name FROM customers")
    customers = c.fetchall()
    conn.close()
    return render_template('rentals.html', rentals=rentals, items=items, customers=customers)
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
