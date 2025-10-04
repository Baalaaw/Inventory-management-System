from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

DATABASE = 'inventory.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            description TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY,
            location_name TEXT NOT NULL,
            address TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_movements (
            movement_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            from_location TEXT,
            to_location TEXT,
            product_id TEXT NOT NULL,
            qty INTEGER NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (from_location) REFERENCES locations(location_id),
            FOREIGN KEY (to_location) REFERENCES locations(location_id)
        )
    ''')

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products')
def products():
    conn = get_db()
    products = conn.execute('SELECT * FROM products ORDER BY product_id').fetchall()
    conn.close()
    return render_template('products.html', products=products)

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product_id = request.form['product_id']
        product_name = request.form['product_name']
        description = request.form.get('description', '')

        conn = get_db()
        try:
            conn.execute('INSERT INTO products (product_id, product_name, description) VALUES (?, ?, ?)',
                        (product_id, product_name, description))
            conn.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('products'))
        except sqlite3.IntegrityError:
            flash('Product ID already exists!', 'error')
        finally:
            conn.close()

    return render_template('product_form.html', action='Add', product=None)

@app.route('/products/edit/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db()

    if request.method == 'POST':
        product_name = request.form['product_name']
        description = request.form.get('description', '')

        conn.execute('UPDATE products SET product_name = ?, description = ? WHERE product_id = ?',
                    (product_name, description, product_id))
        conn.commit()
        conn.close()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products'))

    product = conn.execute('SELECT * FROM products WHERE product_id = ?', (product_id,)).fetchone()
    conn.close()
    return render_template('product_form.html', action='Edit', product=product)

@app.route('/products/delete/<product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM products WHERE product_id = ?', (product_id,))
        conn.commit()
        flash('Product deleted successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Cannot delete product with existing movements!', 'error')
    finally:
        conn.close()
    return redirect(url_for('products'))

@app.route('/locations')
def locations():
    conn = get_db()
    locations = conn.execute('SELECT * FROM locations ORDER BY location_id').fetchall()
    conn.close()
    return render_template('locations.html', locations=locations)

@app.route('/locations/add', methods=['GET', 'POST'])
def add_location():
    if request.method == 'POST':
        location_id = request.form['location_id']
        location_name = request.form['location_name']
        address = request.form.get('address', '')

        conn = get_db()
        try:
            conn.execute('INSERT INTO locations (location_id, location_name, address) VALUES (?, ?, ?)',
                        (location_id, location_name, address))
            conn.commit()
            flash('Location added successfully!', 'success')
            return redirect(url_for('locations'))
        except sqlite3.IntegrityError:
            flash('Location ID already exists!', 'error')
        finally:
            conn.close()

    return render_template('location_form.html', action='Add', location=None)

@app.route('/locations/edit/<location_id>', methods=['GET', 'POST'])
def edit_location(location_id):
    conn = get_db()

    if request.method == 'POST':
        location_name = request.form['location_name']
        address = request.form.get('address', '')

        conn.execute('UPDATE locations SET location_name = ?, address = ? WHERE location_id = ?',
                    (location_name, address, location_id))
        conn.commit()
        conn.close()
        flash('Location updated successfully!', 'success')
        return redirect(url_for('locations'))

    location = conn.execute('SELECT * FROM locations WHERE location_id = ?', (location_id,)).fetchone()
    conn.close()
    return render_template('location_form.html', action='Edit', location=location)

@app.route('/locations/delete/<location_id>', methods=['POST'])
def delete_location(location_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM locations WHERE location_id = ?', (location_id,))
        conn.commit()
        flash('Location deleted successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Cannot delete location with existing movements!', 'error')
    finally:
        conn.close()
    return redirect(url_for('locations'))

@app.route('/movements')
def movements():
    conn = get_db()
    movements = conn.execute('''
        SELECT pm.*, p.product_name,
               fl.location_name as from_loc_name,
               tl.location_name as to_loc_name
        FROM product_movements pm
        JOIN products p ON pm.product_id = p.product_id
        LEFT JOIN locations fl ON pm.from_location = fl.location_id
        LEFT JOIN locations tl ON pm.to_location = tl.location_id
        ORDER BY pm.timestamp DESC
    ''').fetchall()
    conn.close()
    return render_template('movements.html', movements=movements)

@app.route('/movements/add', methods=['GET', 'POST'])
def add_movement():
    conn = get_db()

    if request.method == 'POST':
        movement_id = request.form['movement_id']
        product_id = request.form['product_id']
        from_location = request.form.get('from_location') or None
        to_location = request.form.get('to_location') or None
        qty = int(request.form['qty'])
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not from_location and not to_location:
            flash('At least one location (from or to) must be specified!', 'error')
        else:
            try:
                conn.execute('''
                    INSERT INTO product_movements
                    (movement_id, timestamp, from_location, to_location, product_id, qty)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (movement_id, timestamp, from_location, to_location, product_id, qty))
                conn.commit()
                flash('Movement added successfully!', 'success')
                conn.close()
                return redirect(url_for('movements'))
            except sqlite3.IntegrityError:
                flash('Movement ID already exists!', 'error')

    products = conn.execute('SELECT * FROM products ORDER BY product_name').fetchall()
    locations = conn.execute('SELECT * FROM locations ORDER BY location_name').fetchall()
    conn.close()
    return render_template('movement_form.html', action='Add', movement=None, products=products, locations=locations)

@app.route('/movements/edit/<movement_id>', methods=['GET', 'POST'])
def edit_movement(movement_id):
    conn = get_db()

    if request.method == 'POST':
        product_id = request.form['product_id']
        from_location = request.form.get('from_location') or None
        to_location = request.form.get('to_location') or None
        qty = int(request.form['qty'])

        if not from_location and not to_location:
            flash('At least one location (from or to) must be specified!', 'error')
        else:
            conn.execute('''
                UPDATE product_movements
                SET product_id = ?, from_location = ?, to_location = ?, qty = ?
                WHERE movement_id = ?
            ''', (product_id, from_location, to_location, qty, movement_id))
            conn.commit()
            flash('Movement updated successfully!', 'success')
            conn.close()
            return redirect(url_for('movements'))

    movement = conn.execute('SELECT * FROM product_movements WHERE movement_id = ?', (movement_id,)).fetchone()
    products = conn.execute('SELECT * FROM products ORDER BY product_name').fetchall()
    locations = conn.execute('SELECT * FROM locations ORDER BY location_name').fetchall()
    conn.close()
    return render_template('movement_form.html', action='Edit', movement=movement, products=products, locations=locations)

@app.route('/movements/delete/<movement_id>', methods=['POST'])
def delete_movement(movement_id):
    conn = get_db()
    conn.execute('DELETE FROM product_movements WHERE movement_id = ?', (movement_id,))
    conn.commit()
    conn.close()
    flash('Movement deleted successfully!', 'success')
    return redirect(url_for('movements'))

@app.route('/report')
def report():
    conn = get_db()

    balance_query = '''
        SELECT
            p.product_id,
            p.product_name,
            l.location_id,
            l.location_name,
            COALESCE(
                SUM(CASE WHEN pm.to_location = l.location_id THEN pm.qty ELSE 0 END) -
                SUM(CASE WHEN pm.from_location = l.location_id THEN pm.qty ELSE 0 END),
                0
            ) as balance
        FROM products p
        CROSS JOIN locations l
        LEFT JOIN product_movements pm ON
            p.product_id = pm.product_id AND
            (pm.from_location = l.location_id OR pm.to_location = l.location_id)
        GROUP BY p.product_id, p.product_name, l.location_id, l.location_name
        HAVING balance != 0
        ORDER BY p.product_name, l.location_name
    '''

    balances = conn.execute(balance_query).fetchall()
    conn.close()
    return render_template('report.html', balances=balances)

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
