from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from decimal import Decimal, InvalidOperation
import os
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-development-key')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'bookstore_db'),
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def money(value):
    return float(value or 0)

app.jinja_env.filters['money'] = money


def query_all(sql, params=()):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close(); conn.close()


def query_one(sql, params=()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def init_db():
    # Run schema.sql first; this check helps produce a clear setup message.
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute('''CREATE TABLE IF NOT EXISTS Books (
            book_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            author VARCHAR(150) NOT NULL,
            isbn VARCHAR(20) UNIQUE,
            category VARCHAR(100),
            price DECIMAL(10,2) NOT NULL,
            quantity INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (price >= 0), CHECK (quantity >= 0)
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS Sales (
            sale_id INT AUTO_INCREMENT PRIMARY KEY,
            sale_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            subtotal DECIMAL(10,2) NOT NULL DEFAULT 0,
            discount DECIMAL(10,2) NOT NULL DEFAULT 0,
            tax DECIMAL(10,2) NOT NULL DEFAULT 0,
            total_amount DECIMAL(10,2) NOT NULL
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS Sale_Details (
            detail_id INT AUTO_INCREMENT PRIMARY KEY,
            sale_id INT NOT NULL,
            book_id INT NOT NULL,
            title_at_sale VARCHAR(200) NOT NULL,
            quantity INT NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            line_total DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES Sales(sale_id),
            FOREIGN KEY (book_id) REFERENCES Books(book_id),
            CHECK (quantity > 0), CHECK (unit_price >= 0)
        )''')
        conn.commit()
    finally:
        cur.close(); conn.close()


@app.context_processor
def global_data():
    return {'cart_count': len(session.get('cart', []))}


@app.route('/')
def index():
    try:
        stats = query_one('''SELECT COUNT(*) AS titles, COALESCE(SUM(quantity),0) AS copies,
            COALESCE(SUM(CASE WHEN quantity <= 5 THEN 1 ELSE 0 END),0) AS low_stock FROM Books''')
        sales = query_one("SELECT COUNT(*) AS count, COALESCE(SUM(total_amount),0) AS revenue FROM Sales WHERE DATE(sale_date)=CURDATE()")
        recent = query_all('SELECT sale_id, sale_date, total_amount FROM Sales ORDER BY sale_id DESC LIMIT 5')
        books = query_all('SELECT * FROM Books ORDER BY book_id DESC LIMIT 5')
        return render_template('index.html', stats=stats, sales=sales, recent=recent, books=books)
    except Error as e:
        return render_template('setup_error.html', error=str(e)), 500


@app.route('/books')
def books():
    term = request.args.get('q', '').strip()
    if term:
        like = f'%{term}%'
        rows = query_all('''SELECT * FROM Books WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s OR category LIKE %s ORDER BY title''', (like, like, like, like))
    else:
        rows = query_all('SELECT * FROM Books ORDER BY title')
    return render_template('books.html', books=rows, q=term)


@app.route('/books/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form.get('title', '').strip(); author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip() or None; category = request.form.get('category', '').strip()
        try:
            price = Decimal(request.form.get('price', ''))
            quantity = int(request.form.get('quantity', ''))
            if not title or not author: raise ValueError('Title and author are required.')
            if price < 0 or quantity < 0: raise ValueError('Price and quantity cannot be negative.')
            conn = get_db(); cur = conn.cursor()
            cur.execute('INSERT INTO Books (title, author, isbn, category, price, quantity) VALUES (%s,%s,%s,%s,%s,%s)', (title, author, isbn, category, price, quantity))
            conn.commit(); cur.close(); conn.close()
            flash('Book added to catalogue.', 'success'); return redirect(url_for('books'))
        except (InvalidOperation, ValueError) as e: flash(str(e) or 'Enter a valid price and quantity.', 'error')
        except Error as e: flash('Could not save book. ISBN may already exist. Details: ' + str(e), 'error')
    return render_template('book_form.html', book=None)


@app.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
def edit_book(book_id):
    book = query_one('SELECT * FROM Books WHERE book_id=%s', (book_id,))
    if not book: flash('Book not found.', 'error'); return redirect(url_for('books'))
    if request.method == 'POST':
        try:
            title=request.form.get('title','').strip(); author=request.form.get('author','').strip()
            isbn=request.form.get('isbn','').strip() or None; category=request.form.get('category','').strip()
            price=Decimal(request.form.get('price','')); quantity=int(request.form.get('quantity',''))
            if not title or not author: raise ValueError('Title and author are required.')
            if price < 0 or quantity < 0: raise ValueError('Price and quantity cannot be negative.')
            conn=get_db(); cur=conn.cursor()
            cur.execute('UPDATE Books SET title=%s,author=%s,isbn=%s,category=%s,price=%s,quantity=%s WHERE book_id=%s', (title,author,isbn,category,price,quantity,book_id))
            conn.commit(); cur.close(); conn.close(); flash('Book details updated.', 'success'); return redirect(url_for('books'))
        except (InvalidOperation, ValueError) as e: flash(str(e) or 'Enter valid values.', 'error')
        except Error as e: flash('Could not update book: ' + str(e), 'error')
    return render_template('book_form.html', book=book)


@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if request.method == 'POST':
        try:
            book_id=int(request.form['book_id']); quantity=int(request.form['quantity'])
            if quantity < 0: raise ValueError('Quantity cannot be negative.')
            conn=get_db(); cur=conn.cursor(); cur.execute('UPDATE Books SET quantity=%s WHERE book_id=%s',(quantity,book_id))
            conn.commit(); cur.close(); conn.close(); flash('Inventory quantity updated.', 'success')
        except (ValueError, KeyError): flash('Enter a valid non-negative quantity.', 'error')
        except Error as e: flash('Inventory update failed: '+str(e), 'error')
        return redirect(url_for('inventory'))
    term=request.args.get('q','').strip(); like=f'%{term}%'
    rows=query_all('SELECT * FROM Books WHERE (%s = \'\' OR title LIKE %s OR author LIKE %s OR isbn LIKE %s) ORDER BY quantity ASC, title', (term,like,like,like))
    return render_template('inventory.html', books=rows, q=term)


@app.route('/cart/add', methods=['POST'])
def cart_add():
    try:
        book_id=int(request.form['book_id']); qty=int(request.form.get('quantity','1'))
        book=query_one('SELECT * FROM Books WHERE book_id=%s',(book_id,))
        if not book: raise ValueError('Book not found.')
        if qty <= 0: raise ValueError('Quantity must be greater than zero.')
        cart=session.get('cart',[]); found=False
        for item in cart:
            if item['book_id']==book_id:
                if item['quantity']+qty > book['quantity']: raise ValueError('Requested quantity exceeds available stock.')
                item['quantity']+=qty; found=True; break
        if not found:
            if qty > book['quantity']: raise ValueError('Requested quantity exceeds available stock.')
            cart.append({'book_id':book_id,'title':book['title'],'price':float(book['price']),'quantity':qty})
        session['cart']=cart; flash('Added to sale cart.', 'success')
    except (ValueError, KeyError) as e: flash(str(e), 'error')
    return redirect(request.referrer or url_for('sale'))


@app.route('/cart/update', methods=['POST'])
def cart_update():
    try:
        book_id=int(request.form['book_id']); qty=int(request.form['quantity'])
        if qty <= 0: raise ValueError('Quantity must be at least 1.')
        book=query_one('SELECT quantity FROM Books WHERE book_id=%s',(book_id,))
        if not book or qty>book['quantity']: raise ValueError('Quantity exceeds available stock.')
        cart=session.get('cart',[])
        for item in cart:
            if item['book_id']==book_id: item['quantity']=qty
        session['cart']=cart
    except (ValueError, KeyError) as e: flash(str(e), 'error')
    return redirect(url_for('sale'))


@app.route('/cart/remove/<int:book_id>', methods=['POST'])
def cart_remove(book_id):
    session['cart']=[x for x in session.get('cart',[]) if x['book_id'] != book_id]
    flash('Item removed from cart.', 'success'); return redirect(url_for('sale'))


@app.route('/sale', methods=['GET', 'POST'])
def sale():
    cart=session.get('cart',[]); subtotal=sum(Decimal(str(x['price']))*x['quantity'] for x in cart)
    if request.method=='POST':
        if not cart: flash('Add at least one book before completing a sale.', 'error'); return redirect(url_for('sale'))
        try:
            discount=Decimal(request.form.get('discount','0')); tax_rate=Decimal(request.form.get('tax_rate','0'))
            if discount < 0 or discount > subtotal: raise ValueError('Discount must be between zero and subtotal.')
            if tax_rate < 0 or tax_rate > 100: raise ValueError('Tax rate must be between 0 and 100.')
            tax=((subtotal-discount)*tax_rate/Decimal('100')).quantize(Decimal('0.01'))
            total=subtotal-discount+tax
            conn=get_db(); cur=conn.cursor()
            try:
                conn.start_transaction()
                # Lock and validate all inventory rows before recording the sale.
                locked={}
                for item in cart:
                    cur.execute('SELECT title, price, quantity FROM Books WHERE book_id=%s FOR UPDATE',(item['book_id'],))
                    row=cur.fetchone()
                    if not row or row[2] < item['quantity']:
                        raise ValueError(f"Insufficient stock for {item['title']}. Sale was not completed.")
                    locked[item['book_id']]=row
                cur.execute('INSERT INTO Sales (subtotal,discount,tax,total_amount) VALUES (%s,%s,%s,%s)',(subtotal,discount,tax,total))
                sale_id=cur.lastrowid
                for item in cart:
                    row=locked[item['book_id']]; price=Decimal(str(row[1])); line=price*item['quantity']
                    cur.execute('INSERT INTO Sale_Details (sale_id,book_id,title_at_sale,quantity,unit_price,line_total) VALUES (%s,%s,%s,%s,%s,%s)',(sale_id,item['book_id'],row[0],item['quantity'],price,line))
                    cur.execute('UPDATE Books SET quantity=quantity-%s WHERE book_id=%s',(item['quantity'],item['book_id']))
                conn.commit()
            except Exception:
                conn.rollback(); raise
            finally: cur.close(); conn.close()
            session['cart']=[]; flash(f'Sale #{sale_id} completed successfully.', 'success'); return redirect(url_for('receipt',sale_id=sale_id))
        except (InvalidOperation, ValueError) as e: flash(str(e), 'error')
        except Error as e: flash('Database error; sale was rolled back. '+str(e), 'error')
    return render_template('sale.html', cart=cart, subtotal=subtotal)


@app.route('/history')
def history():
    sales=query_all('SELECT * FROM Sales ORDER BY sale_date DESC, sale_id DESC LIMIT 200')
    return render_template('history.html', sales=sales)


@app.route('/receipt/<int:sale_id>')
def receipt(sale_id):
    sale=query_one('SELECT * FROM Sales WHERE sale_id=%s',(sale_id,))
    if not sale: flash('Receipt not found.', 'error'); return redirect(url_for('history'))
    items=query_all('SELECT * FROM Sale_Details WHERE sale_id=%s',(sale_id,))
    return render_template('receipt.html', sale=sale, items=items)


@app.route('/health')
def health():
    try:
        query_one('SELECT 1 AS ok'); return jsonify(status='ok', database='connected')
    except Error as e: return jsonify(status='error', message=str(e)), 500


if __name__ == '__main__':
    try: init_db()
    except Error as e: print('Database setup error:', e, '\nCreate the database and configure DB_* environment variables.')
    app.run(debug=os.getenv('FLASK_DEBUG','0')=='1', host='127.0.0.1', port=int(os.getenv('PORT','5000')))
