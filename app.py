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



@app.route("/signup", methods=['GET', 'POST'])
def signup_page():
    if request.method == 'POST':
        # 1. Get data from form
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # 2. Check if user already exists
        if email in users_db:
            return "<h1>Error: User already exists!</h1> <a href='/login'>Login</a>"
            
        # 3. Save User to DB
        users_db[email] = {
            'password': password,
            'name': name,
            'addresses': []
        }
        
        return redirect(url_for('login_page'))
        
    return render_template("signup.html")

@app.route("/login", methods=['GET', 'POST'])
def login_page():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # 1. CHECK ADMIN
        if email == "admin@bookstore.com":
            if password == "admin123":
                session['role'] = 'admin'
                return redirect(url_for('admin_page'))
            else:
                return "<h1>Wrong Admin Password!</h1> <a href='/login'>Try Again</a>"
            
        # 2. CHECK NORMAL USER
        if email in users_db:
            # Check if password matches the one stored in users_db
            if users_db[email]['password'] == password:
                session['role'] = 'user'
                session['user_email'] = email
                return redirect(url_for('home'))
            else:
                return "<h1>Wrong Password!</h1> <a href='/login'>Try Again</a>"
        else:
            return "<h1>User not found! Please Sign Up first.</h1> <a href='/signup'>Sign Up</a>"
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear() 
    return redirect(url_for('login_page'))

# --- ADMIN ---
@app.route("/admin")
def admin_page():
    if session.get('role') != 'admin': return "<h1>Access Denied</h1>"
    return render_template("admin.html")

@app.route("/add_book", methods=['POST'])
def add_book():
    if session.get('role') != 'admin': return redirect(url_for('home'))
    
    title = request.form['title']
    author = request.form['author']
    original_price = int(request.form['price'])
    stock = int(request.form['stock'])
    offer_text = request.form.get('offer_text', '') 
    
    sale_input = request.form.get('sale_price')
    sale_price = int(sale_input) if sale_input else None
    
    new_book = {
        "title": title, "author": author, "price": original_price,
        "sale_price": sale_price, "stock": stock, "offer_text": offer_text
    }
    books_db.append(new_book)
    return redirect(url_for('admin_page'))

# --- CART LOGIC ---
@app.route("/add_to_cart/<book_title>")
def add_to_cart(book_title):
    if 'role' not in session: return redirect(url_for('login_page'))
    
    book = get_book_by_title(book_title)
    if not book or book['stock'] <= 0: return "<h1>Out of Stock</h1> <a href='/'>Back</a>"
    final_price = book['sale_price'] if book['sale_price'] else book['price']

    for item in cart_db:
        if item['title'] == book_title:
            if item['quantity'] + 1 > book['stock']: return "<h1>Not enough stock!</h1> <a href='/'>Back</a>"
            item['quantity'] += 1; return redirect(url_for('home'))
            
    cart_db.append({"title": book['title'], "author": book['author'], "price": final_price, "quantity": 1})
    return redirect(url_for('home'))

@app.route("/cart")
def view_cart():
    if 'role' not in session: return redirect(url_for('login_page'))
    total_price = sum(item['price'] * item['quantity'] for item in cart_db)
    return render_template("cart.html", cart=cart_db, total=total_price)

# --- CHECKOUT ---
@app.route("/checkout", methods=['GET', 'POST'])
def checkout():
    if 'role' not in session: return redirect(url_for('login_page'))
    
    email = session.get('user_email')
    # Safety Check: If server restarted, user might be logged in but not in DB
    if email not in users_db: users_db[email] = {'addresses': [], 'password': 'temp_password'} 

    user_addresses = users_db[email]['addresses']
    total_price = sum(item['price'] * item['quantity'] for item in cart_db)
    
    if request.method == 'POST':
        selected_addr = request.form.get('selected_address') or request.form.get('new_address')
        if request.form.get('new_address'): users_db[email]['addresses'].append(request.form.get('new_address'))
        payment_mode = request.form['payment_mode']
        
        # Reduce Stock
        for cart_item in cart_db:
            for book in books_db:
                if book['title'] == cart_item['title']: book['stock'] -= cart_item['quantity']
        
        cart_db.clear()
        return render_template("order_success.html", address=selected_addr, payment=payment_mode)

    return render_template("checkout.html", addresses=user_addresses, total=total_price)

# --- OTHER ROUTES ---
@app.route("/increase_quantity/<book_title>")
def increase_quantity(book_title):
    book_inv = get_book_by_title(book_title)
    for item in cart_db:
        if item['title'] == book_title:
            if item['quantity'] + 1 <= book_inv['stock']: item['quantity'] += 1
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
    
    # 1. Check if book is ALREADY in wishlist
    for item in wishlist_db:
        if item['title'] == book_title:
            
            return redirect(url_for('home'))

    
    book = get_book_by_title(book_title)
    if book: 
        wishlist_db.append(book)
        
    return redirect(url_for('home'))
@app.route("/remove_from_wishlist/<book_title>")
def remove_from_wishlist(book_title):
    global wishlist_db
    wishlist_db = [item for item in wishlist_db if item['title'] != book_title]
    return redirect(url_for('view_wishlist'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
