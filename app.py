from flask import Flask, request, url_for, render_template, redirect, flash, make_response,session, abort, jsonify
from data import ROLLS_DATA, BEVERAGE_DATA
from forms import signupForm, loginForm, ChangePasswordForm

from globals import database  # ✅ import from globals instead


PRODUCTS_DATA = {**ROLLS_DATA, **BEVERAGE_DATA}

from datetime import timedelta, datetime
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean


from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash



#  App & database config
BASE_DIR = Path(__file__).parent

app = Flask(__name__)
app.config.update(
    SECRET_KEY="change-this-in-prod",
    # ───────────────  Local dev: SQLite  ───────────────
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{BASE_DIR / 'bitemyroll.db'}",
    # ───────────────  Prod example: MySQL on PythonAnywhere  ───────────────
    # SQLALCHEMY_DATABASE_URI="mysql+pymysql://USER:PASSWORD@USER.mysql.pythonanywhere-services.com/USER$DB",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    REMEMBER_COOKIE_DURATION=timedelta(days=30),
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=1440),
)

db = SQLAlchemy(app)



#  Database models
class User(db.Model, UserMixin):
    id       = db.Column(db.Integer, primary_key=True)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80),  nullable=False)
    pw_hash  = db.Column(db.String(512), nullable=False)
    gender   = db.Column(db.String(10))
    dob      = db.Column(db.Date)
    is_admin = db.Column(db.Boolean, default=False)  
    #location
    street_road = db.Column(db.String(200))
    ward = db.Column(db.String(100))
    area = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    pickup_point = db.Column(db.String(200))
    drinks_visited = db.Column(Boolean, default=False)




#  Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))

from app import app
for r in app.url_map.iter_rules():
    print(r.endpoint, "→", r.rule)


@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html', title="BiteMyRoll: Rolling Happiness to Your Doorstep")

@app.route('/menu')
def menu():
    return render_template('menu.html', title="Today's menu")

@app.route('/contact')
def contact():
    return render_template('contact.html', title="Contact Us")

@app.route('/about')
def about():
    return render_template('about.html', title="About Us")

@app.route('/detail/<type>')
def detail(type):
    return render_template('roll_detail.html', roll=ROLLS_DATA[type], title=f"BiteMyRole - {ROLLS_DATA[type]["name"]}", roll_key=type)

# ──────────  Sign-up  ──────────
@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = signupForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered", "error")
        else:
            user = User(
                email    = form.email.data,
                username = form.username.data,
                pw_hash  = generate_password_hash(form.password.data),
                gender   = form.gender.data or None,
                dob      = form.dob.data,
            )
            db.session.add(user)
            db.session.commit()

            login_user(user)  # ✅ Logs in the new user session

            flash("Signed up and logged in successfully!", "success")
            return redirect(url_for("menu"))
    return render_template("signup.html", form=form)

# ──────────  Login  ──────────
@app.route("/login", methods=["GET", "POST"])
def login():
    form = loginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        print("Entered password:", form.password.data)
        print("Stored hash:", user.pw_hash if user else "No user")

        if user and check_password_hash(user.pw_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Login successful!", "success")
            if user.is_admin:
                return redirect(url_for("admin_orders"))  # or whatever your admin home is
            return redirect(url_for("menu"))


        flash("Invalid credentials", "error")
    return render_template("login.html", form=form)

# ──────────  Logout  ──────────
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You’ve been logged out.", "info")
    return redirect(url_for("home"))

# ──────────  CLI helper to create tables  ──────────
@app.cli.command("init-db")
def init_db():
    """Run `flask init-db` once to create all tables."""
    db.create_all()
    print("✓ Database tables created")


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(current_user.pw_hash, form.current_password.data):
            flash("Current password is incorrect.", "error")
        else:
            current_user.pw_hash = generate_password_hash(form.password.data)
            db.session.commit()
            flash("Password updated successfully!", "success")
            return redirect(request.referrer or url_for("menu"))
    return render_template("change_password.html", form=form, title="Change Password")

# ─────────────────────────────────────────────────────────
#  Cart & Orders
# ─────────────────────────────────────────────────────────

class CartItem(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    user_id  = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    roll_id  = db.Column(db.String(40), nullable=False)     # e.g. "paneer_tikka"
    size     = db.Column(db.String(20), nullable=False)     # e.g. "Regular"
    qty      = db.Column(db.Integer,  nullable=False, default=1)
    notes    = db.Column(db.Text) 

class OrderItem(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    order_id  = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    roll_id   = db.Column(db.String(40), nullable=False)
    size      = db.Column(db.String(20), nullable=False)    # NEW
    qty       = db.Column(db.Integer, nullable=False)
    price_each= db.Column(db.Float,   nullable=False)
    notes    = db.Column(db.Text) 

class Order(db.Model):
    __tablename__ = "order"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Pending") 
    total = db.Column(db.Float, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")


from urllib.parse import urlparse

@app.route("/add-to-cart/<roll_key>", methods=["POST"])
@login_required
def add_to_cart(roll_key):
    roll  = PRODUCTS_DATA.get(roll_key) or abort(404)
    notes = request.form.get("notes", "").strip()

    has_quantity = False

    for s in roll["sizes"]:
        field = f"qty_{s['label']}"
        qty   = int(request.form.get(field, 0))
        if qty <= 0:
            continue

        has_quantity = True

        item = CartItem.query.filter_by(
            user_id = current_user.id,
            roll_id = roll_key,
            size    = s["label"]
        ).first()

        if item:
            item.qty   += qty
            item.notes  = notes
        else:
            db.session.add(CartItem(
                user_id = current_user.id,
                roll_id = roll_key,
                size    = s["label"],
                qty     = qty,
                notes   = notes
            ))

    if not has_quantity:
        flash("Please select at least one item to add to cart.", "warning")
        return redirect(request.referrer or url_for("menu"))

    db.session.commit()
    flash("Added to cart!", "success")

    # 🧭 Check where user came from
    ref_path = urlparse(request.referrer).path if request.referrer else ""
    
    if "/drinksDetail" in ref_path:
        return redirect(url_for("drinksMenu"))
    elif "/detail" in ref_path:
        return redirect(url_for("menu"))
    else:
        return redirect(url_for("cart"))




@app.route("/orders")
@login_required
def orders():
    raw_orders = (Order.query
                  .filter_by(user_id=current_user.id)
                  .order_by(Order.placed_at.desc())
                  .all())

    results = []
    for o in raw_orders:
        item_rows = OrderItem.query.filter_by(order_id=o.id).all()
        rows = [{
            "name":       PRODUCTS_DATA[i.roll_id]["name"],
            "size":       i.size,
            "qty":        i.qty,
            "price_each": i.price_each,
            "notes": i.notes
        } for i in item_rows]

        results.append({"order_obj": o, "rows": rows})   # ← keys renamed
    return render_template("orders.html", orders=results)


@app.route("/cart")
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    rows, total = [], 0
    for ci in cart_items:
        roll  = PRODUCTS_DATA[ci.roll_id]
        size  = ci.size
        price = next(p["price"] for p in roll["sizes"] if p["label"] == size)
        sub   = price * ci.qty
        total += sub
        rows.append({
            "id": ci.id,
            "name": roll["name"],
            "size": size,
            "qty": ci.qty,
            "price": price,
            "subtotal": sub
        })

    # Pass location info to frontend as JSON
    location_data = {
        "street_road": current_user.street_road or "",
        "area": current_user.area or "",
        "pincode": current_user.pincode or ""
    }

    return render_template("cart.html", rows=rows, total=total, location_data=location_data)




@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))

    # 1) create Order
    total = 0
    for ci in cart_items:
        roll = PRODUCTS_DATA[ci.roll_id]
        price = next(size["price"] for size in roll["sizes"] if size["label"] == ci.size)
        total += price * ci.qty

    order = Order(user_id=current_user.id, total=total)
    db.session.add(order)
    db.session.flush()  # get order.id

    # 2) move CartItems into OrderItems (WITH SIZE!)
    for ci in cart_items:
        roll = PRODUCTS_DATA[ci.roll_id]
        price = next(size["price"] for size in roll["sizes"] if size["label"] == ci.size)
        db.session.add(OrderItem(
            order_id   = order.id,
            roll_id    = ci.roll_id,
            size       = ci.size,               # ✅ Add size here
            qty        = ci.qty,
            price_each = price,
            notes      = ci.notes
        ))
        db.session.delete(ci)
    current_user.drinks_visited = False
    db.session.add(current_user)  # ✅ Explicitly mark user for update
    db.session.commit()
    flash("Order placed! 🎉", "success")
    return redirect(url_for("orders"))


@app.route("/cancel-order/<int:order_id>", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    db.session.delete(order)         # relationship takes care of its OrderItems
    db.session.commit()
    flash("Order cancelled.", "info")
    return redirect(url_for("orders"))

@app.route("/update-cart/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id):
    op   = request.form.get("op")            # "inc" or "dec"
    item = CartItem.query.filter_by(
        id=item_id, user_id=current_user.id
    ).first_or_404()

    if op == "inc":
        item.qty += 1

    elif op == "dec":
        item.qty -= 1
        if item.qty <= 0:
            db.session.delete(item)          # auto-delete at 0

    db.session.commit()
    return redirect(url_for("cart"))

@app.route('/drinks')
@login_required
def drinksMenu():
    if not current_user.drinks_visited:
        current_user.drinks_visited = True
        db.session.commit()  # ✅ Save to DB
    return render_template('drinksMenu.html', title="Beverages")


@app.route('/drinksDetail/<type>', methods=["GET", "POST"])
def drinksDetail(type):
    return render_template('drinks_detail.html', roll=BEVERAGE_DATA[type], title=f"BiteMyRole - {type}", roll_key=type)

@app.route("/set_location", methods=["POST"])
@login_required
def set_location():
    data = request.get_json()

    current_user.street_road = data.get("street_road")
    current_user.ward = data.get("ward")
    current_user.area = data.get("area")
    current_user.pincode = data.get("pincode")
    current_user.state = data.get("state")
    current_user.country = data.get("country")
    current_user.pickup_point = data.get("pickup_point")

    db.session.commit()

    return jsonify({
        "street_road": current_user.street_road,
        "ward": current_user.ward,
        "area": current_user.area,
        "pincode": current_user.pincode,
        "state": current_user.state,
        "country": current_user.country,
        "pickup_point": current_user.pickup_point
    })


@app.context_processor
def inject_database():
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        rows, total = [], 0
        for ci in cart_items:
            roll = PRODUCTS_DATA[ci.roll_id]
            size = ci.size
            price = next(p["price"] for p in roll["sizes"] if p["label"] == size)
            sub = price * ci.qty
            total += sub    
            rows.append({
                "name": roll["name"],
                "size": size,
                "qty": ci.qty,
                "price": price,
                "subtotal": sub
            })
        return dict(cart_data=rows, cart_total=total)
    return dict(cart_data=[], cart_total=0)


@app.route('/map')
def map():
    return render_template("map.html")



@app.route("/admin/orders")
@login_required
def admin_orders():
    if not current_user.is_admin:
        abort(403)

    orders = Order.query.order_by(Order.placed_at.asc()).all()
    order_data = []

    for order in orders:
        user = User.query.get(order.user_id)
        items = OrderItem.query.filter_by(order_id=order.id).all()

        item_list = []
        for item in items:
            product = PRODUCTS_DATA.get(item.roll_id, {})
            item_list.append({
                "name": product.get("name", item.roll_id),
                "size": item.size,
                "qty": item.qty,
                "price_each": item.price_each,
                "notes": item.notes
            })

        order_data.append({
            "order_id": order.id,
            "placed_at": order.placed_at.strftime("%Y-%m-%d %H:%M"),
            "status": order.status,
            "total": order.total,
            "user": {
                "username": user.username,
                "email": user.email,
                "location": f"{user.street_road}, {user.area}, {user.pincode}, {user.state}, {user.country}",
                "pickup": f"{user.pickup_point}"
            },
            "order_items": item_list   # ← renamed to avoid conflict
        })


    return render_template("admin/admin_orders.html", orders=order_data, title="All Orders")


@app.route("/admin/update_status/<int:order_id>", methods=["POST"])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        abort(403)

    order = Order.query.get_or_404(order_id)
    action = request.form.get("action")

    if action == "cancel":
        order.status = "Cancelled"
    elif action == "update":
        new_status = request.form.get("status")
        if new_status not in ["Processing", "Out for Delivery", "Delivered"]:
            return "Invalid status", 400
        order.status = new_status
    else:
        return "Unknown action", 400

    db.session.commit()
    flash(f"Order #{order.id} status updated to {order.status}", "success")
    return redirect(url_for("admin_orders"))





if __name__ == '__main__':
    app.run(debug=True)

