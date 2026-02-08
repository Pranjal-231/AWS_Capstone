from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "my_secret_key" 

# --- DATABASES ---
books_db = []      
cart_db = []       
wishlist_db = []   
users_db = {} 

# --- HELPER ---
def get_book_by_title(title):
    for book in books_db:
        if book['title'] == title:
            return book
    return None

# --- ROUTES ---

@app.route("/")
def home():
    user_role = session.get('role', 'guest') 
    total_qty = sum(item['quantity'] for item in cart_db)
    return render_template("index.html", books=books_db, cart_count=total_qty, role=user_role)

# --- ADMIN ---
@app.route("/admin")
def admin_page():
    if session.get('role') != 'admin': return "Access Denied"
    return render_template("admin.html")

@app.route("/add_book", methods=['POST'])
def add_book():
    if session.get('role') != 'admin': return redirect(url_for('home'))
    
    # 1. Capture Basic Info
    title = request.form['title']
    author = request.form['author']
    original_price = int(request.form['price'])
    
    # 2. Capture New Features (Stock, Sale, Offer)
    stock = int(request.form['stock'])
    offer_text = request.form.get('offer_text', '') # Optional text like "50% Off"
    
    # Check if there is a Sale Price (Empty string means NO sale)
    sale_input = request.form.get('sale_price')
    sale_price = int(sale_input) if sale_input else None
    
    # 3. Save to DB
    new_book = {
        "title": title, 
        "author": author, 
        "price": original_price,
        "sale_price": sale_price,  # If this exists, it overrides price
        "stock": stock,
        "offer_text": offer_text
    }
    books_db.append(new_book)
    
    return redirect(url_for('admin_page'))

# --- CART LOGIC (Updated for Stock & Sale Price) ---

@app.route("/add_to_cart/<book_title>")
def add_to_cart(book_title):
    if 'role' not in session: return redirect(url_for('login_page'))
    
    book = get_book_by_title(book_title)
    
    # 1. Check Stock
    if not book or book['stock'] <= 0:
        return "<h1>Error: Out of Stock</h1> <a href='/'>Back</a>"

    # 2. Determine Final Price (Sale vs Original)
    final_price = book['sale_price'] if book['sale_price'] else book['price']

    # 3. Add to Cart
    for item in cart_db:
        if item['title'] == book_title:
            # Check if adding one more exceeds stock
            if item['quantity'] + 1 > book['stock']:
                return "<h1>Error: Not enough stock available!</h1> <a href='/'>Back</a>"
            item['quantity'] += 1
            return redirect(url_for('home'))
            
    # New Item
    cart_db.append({
        "title": book['title'], 
        "author": book['author'], 
        "price": final_price, 
        "quantity": 1
    })
    return redirect(url_for('home'))

@app.route("/cart")
def view_cart():
    if 'role' not in session: return redirect(url_for('login_page'))
    total_price = sum(item['price'] * item['quantity'] for item in cart_db)
    return render_template("cart.html", cart=cart_db, total=total_price)

# --- CHECKOUT (Reduces Stock) ---
@app.route("/checkout", methods=['GET', 'POST'])
def checkout():
    if 'role' not in session: return redirect(url_for('login_page'))
    
    email = session.get('user_email')
    if email not in users_db: users_db[email] = {'addresses': []} # Safety check

    user_addresses = users_db[email]['addresses']
    total_price = sum(item['price'] * item['quantity'] for item in cart_db)
    
    if request.method == 'POST':
        # 1. Handle Address & Payment
        selected_address = request.form.get('selected_address') or request.form.get('new_address')
        if request.form.get('new_address'):
             users_db[email]['addresses'].append(request.form.get('new_address'))
        payment_mode = request.form['payment_mode']
        
        # 2. CRITICAL: REDUCE STOCK from Main Inventory
        for cart_item in cart_db:
            for book in books_db:
                if book['title'] == cart_item['title']:
                    book['stock'] -= cart_item['quantity']
        
        # 3. Clear Cart
        cart_db.clear()
        return render_template("order_success.html", address=selected_address, payment=payment_mode)

    return render_template("checkout.html", addresses=user_addresses, total=total_price)

# --- OTHER ROUTES (Standard) ---
@app.route("/increase_quantity/<book_title>")
def increase_quantity(book_title):
    book_in_inventory = get_book_by_title(book_title)
    for item in cart_db:
        if item['title'] == book_title:
            # Don't let user buy more than available stock
            if item['quantity'] + 1 <= book_in_inventory['stock']:
                item['quantity'] += 1
            break
    return redirect(url_for('view_cart'))

@app.route("/decrease_quantity/<book_title>")
def decrease_quantity(book_title):
    global cart_db
    for item in cart_db:
        if item['title'] == book_title:
            item['quantity'] -= 1
            if item['quantity'] <= 0: cart_db = [x for x in cart_db if x['title'] != book_title]; break
    return redirect(url_for('view_cart'))

@app.route("/remove_from_cart/<book_title>")
def remove_from_cart(book_title):
    global cart_db
    cart_db = [item for item in cart_db if item['title'] != book_title]
    return redirect(url_for('view_cart'))

@app.route("/wishlist")
def view_wishlist(): return render_template("wishlist.html", wishlist=wishlist_db)
@app.route("/add_to_wishlist/<book_title>")
def add_to_wishlist(book_title):
    if 'role' not in session: return redirect(url_for('login_page'))
    book = get_book_by_title(book_title)
    if book: wishlist_db.append(book)
    return redirect(url_for('home'))
@app.route("/remove_from_wishlist/<book_title>")
def remove_from_wishlist(book_title):
    global wishlist_db
    wishlist_db = [item for item in wishlist_db if item['title'] != book_title]
    return redirect(url_for('view_wishlist'))
@app.route("/login", methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email, pwd = request.form['email'], request.form['password']
        if email == "p@123.com" and pwd == "123":
            session['role'] = 'admin'; return redirect(url_for('admin_page'))
        session['role'] = 'user'; session['user_email'] = email
        if email not in users_db: users_db[email] = {'addresses': []}
        return redirect(url_for('home'))
    return render_template("login.html")
@app.route("/logout")
def logout(): session.clear(); return redirect(url_for('login_page'))
@app.route("/signup")
def signup_page(): return render_template("signup.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)