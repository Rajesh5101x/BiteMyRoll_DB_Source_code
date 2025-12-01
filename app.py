from flask import Flask, request, url_for, render_template, redirect, flash, make_response,session, abort, jsonify
from forms import signupForm, loginForm, ChangePasswordForm, ContactForm, ResetPasswordForm, ForgotPasswordForm, CreateUserForm

from globals import database  
import uuid


from flask_socketio import SocketIO, emit, join_room

from datetime import timedelta, datetime
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, func
from flask_migrate import Migrate

from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import socket


def get_lan_ip():
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        print(f'Your local ip is :- http://{ip_address}:5000')
        return ip_address
    except Exception:
        print('Failed to get LAN IP. Using localhost:5000')
        return '127.0.0.1'
    finally:
        if s:
            s.close()



BASE_DIR = Path(__file__).parent

app = Flask(__name__)
app.config.update(
    SECRET_KEY="change-this-in-prod",
    SQLALCHEMY_DATABASE_URI=f"mysql+pymysql://BiteMyRollOffici:rr9437664323@BiteMyRollOfficial.mysql.pythonanywhere-services.com/BiteMyRollOffici$BiteMyRoll2",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    REMEMBER_COOKIE_DURATION=timedelta(days=30),
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=1440)
)

#SERVER_NAME='192.168.43.187:5000', 
#SERVER_NAME=f'{get_lan_ip()}:5000'

db = SQLAlchemy(app)
migrate = Migrate(app, db) 
import os
UPLOAD_DIR = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

class Product(db.Model):
    __tablename__ = "products"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)  
    image = db.Column(db.String(255), nullable=True)
    diet = db.Column(db.String(20), nullable=True)       
    description = db.Column(db.Text, nullable=False)

    sizes = db.relationship("ProductSize", backref="product", cascade="all, delete-orphan")

class ProductSize(db.Model):
    __tablename__ = "product_sizes"
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    label = db.Column(db.String(50), nullable=False)     
    price = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)  



@app.cli.command("seed-db")
def seed_db():
    from data import ROLLS_DATA, BEVERAGE_DATA

    for roll in ROLLS_DATA.values():
        if not Product.query.filter_by(name=roll["name"]).first():
            product = Product(
                name=roll["name"],
                category="Roll",
                image=roll.get("image"),
                diet=roll.get("diet"),
                description=roll["desc"]
            )
            db.session.add(product)
            db.session.flush()
            for size in roll["sizes"]:
                db.session.add(ProductSize(product_id=product.id, label=size["label"], price=size["price"]))

    for bev in BEVERAGE_DATA.values():
        if not Product.query.filter_by(name=bev["name"]).first():
            product = Product(
                name=bev["name"],
                category="Beverage",
                image=bev.get("image"),
                description=bev["desc"]
            )
            db.session.add(product)
            db.session.flush()
            for size in bev["sizes"]:
                db.session.add(ProductSize(product_id=product.id, label=size["label"], price=size["price"]))

    db.session.commit()
    print("✓ Products seeded successfully!")


def get_product_data(identifier=None):
    if identifier is not None:
        try:
            pid = int(identifier)
            product = Product.query.get(pid)
        except (TypeError, ValueError):
            product = None

        if not product:
            product = Product.query.filter_by(name=str(identifier)).first()

        if not product:
            return None

        return {
            "name": product.name,
            "image": product.image,
            "diet": product.diet,
            "desc": product.description,
            "sizes": [{"id": s.id, "label": s.label, "price": s.price, "available": s.is_available} for s in product.sizes],
        }

    products_dict = {}
    products = Product.query.all()
    for p in products:
        products_dict[p.name] = {
            "name": p.name,
            "image": p.image,
            "diet": p.diet,
            "desc": p.description,
            "sizes": [{"label": s.label, "price": s.price} for s in p.sizes],
        }
    return products_dict


class User(db.Model, UserMixin):
    id       = db.Column(db.Integer, primary_key=True)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    username = db.Column(db.String(80),  nullable=False)
    pw_hash  = db.Column(db.String(512), nullable=False)
    gender   = db.Column(db.String(10))
    dob      = db.Column(db.Date)
    is_admin = db.Column(db.Integer, default=0) 
    cash_due_by_delivery_boy = db.Column(db.Numeric(10, 2), default=0.00)
    street_road = db.Column(db.String(200))
    ward = db.Column(db.String(100))
    area = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    pickup_point = db.Column(db.String(200))
    drinks_visited = db.Column(Boolean, default=False)
    lat = db.Column(db.Float, nullable=True) 
    lon = db.Column(db.Float, nullable=True) 
    

    def set_password(self, password):
        self.pw_hash = generate_password_hash(password)


    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def is_admin_user(self):
        return self.is_admin == 1

    def is_staff_user(self):
        return self.is_admin == 2

    def is_delivery_user(self):
        return self.is_admin == 3



login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))

@app.errorhandler(404)
def not_found(e):
    return """
    <html>
      <head><title>Reloading...</title></head>
      <body>
        <script>
          if (document.referrer) {
            // Go back and reload parent page
            window.location.href = document.referrer;
          } else {
            // If no referrer, just go home
            window.location.href = "/";
          }
        </script>
      </body>
    </html>
    """, 404



@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html', title="BiteMyRoll: Rolling Happiness to Your Doorstep")

@app.route('/menu')
def menu():
    rolls = Product.query.filter_by(category="Roll").all()
    return render_template('menu.html', title="Today's menu", rolls=rolls)



@app.route('/about')
def about():
    return render_template('about.html', title="About Us")

@app.route('/detail/<type>')
def detail(type):
    roll = get_product_data(type)  
    if not roll:
        abort(404)
    return render_template(
        'roll_detail.html',
        roll=roll,
        title=f"BiteMyRoll - {roll['name']}",
        roll_key=type
    )


@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = signupForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered", "error")
        else:
            user = User(
                email    = form.email.data,
                phone   = form.phone.data,
                username = form.username.data,
                pw_hash  = generate_password_hash(form.password.data),
                gender   = form.gender.data or None,
                dob      = form.dob.data,
            )
            db.session.add(user)
            db.session.commit()

            login_user(user)  

            flash("Signed up and logged in successfully!", "success")
            return redirect(url_for("menu"))
    return render_template("signup.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = loginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.pw_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Login successful!", "success") 
            if user.is_admin == 2:
                return redirect(url_for("maker_orders"))
            if user.is_admin == 3:
                return redirect(url_for("delivery_orders"))
            if user.is_admin:
                return redirect(url_for("admin_orders")) 
            return redirect(url_for("menu"))

        flash("Invalid credentials", "error")
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You’ve been logged out.", "info")
    return redirect(url_for("home"))

@app.cli.command("init-db")
def init_db():
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


class CartItem(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    user_id  = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    roll_id  = db.Column(db.String(40), nullable=False)     
    size     = db.Column(db.String(20), nullable=False)     
    qty      = db.Column(db.Integer,  nullable=False, default=1)
    notes    = db.Column(db.Text) 

class OrderItem(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    order_id  = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    roll_id   = db.Column(db.String(40), nullable=False)
    size      = db.Column(db.String(20), nullable=False)    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    payment_status = db.Column(db.String(20), default="pending")  # pending, paid, failed
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    prepared_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)   # staff/admin ID
    delivered_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)  # delivery boy ID
    qr_code = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))



from urllib.parse import urlparse

@app.route("/add-to-cart/<roll_key>", methods=["POST"])
@login_required
def add_to_cart(roll_key):
    roll  = get_product_data(roll_key) or abort(404)
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
            "name": get_product_data(i.roll_id)["name"],
            "size":       i.size,
            "qty":        i.qty,
            "price_each": i.price_each,
            "notes": i.notes
        } for i in item_rows]

        results.append({"order_obj": o, "rows": rows,"payment_status": o.payment_status,"payment_method": o.payment_method})   
    return render_template("orders.html", orders=results)


@app.route("/cart")
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    rows, total = [], 0
    for ci in cart_items:
        roll  = get_product_data(ci.roll_id)
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

    
    location_data = {
        "street_road": current_user.street_road or "",
        "area": current_user.area or "",
        "pincode": current_user.pincode or ""
    }

    return render_template("cart.html", rows=rows, total=total, location_data=location_data)




import qrcode
import os
from datetime import datetime
 

IST_OFFSET = timedelta(hours=5, minutes=30)

@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))

    total = 0
    for ci in cart_items:
        roll = get_product_data(ci.roll_id)
        price = next(size["price"] for size in roll["sizes"] if size["label"] == ci.size)
        total += price * ci.qty

    amount_in_paise = int(total * 100)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "inr",
                "product_data": {"name": "BiteMyRoll Order"},
                "unit_amount": amount_in_paise,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=url_for("payment_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=url_for("payment_cancel", _external=True),
    )

    return redirect(session.url, code=303)



@app.route("/checkout/cod", methods=["POST"])
@login_required
def checkout_cod():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))

    total = sum(ci.qty * next(size["price"] for size in get_product_data(ci.roll_id)["sizes"] if size["label"] == ci.size) for ci in cart_items)

    qr_code_str = str(uuid.uuid4())
    order = Order(
        user_id=current_user.id,
        total=total,
        qr_code=qr_code_str,
        placed_at=datetime.utcnow() + IST_OFFSET,
        created_at=datetime.utcnow() + IST_OFFSET,
        payment_status="not paid",
        payment_method="COD"
    )
    db.session.add(order)
    db.session.flush()

    for ci in cart_items:
        roll = get_product_data(ci.roll_id)
        price = next(size["price"] for size in roll["sizes"] if size["label"] == ci.size)
        db.session.add(OrderItem(
            order_id=order.id,
            roll_id=ci.roll_id,
            size=ci.size,
            qty=ci.qty,
            price_each=price,
            notes=ci.notes
        ))
        db.session.delete(ci)

    qr = qrcode.make(f"{qr_code_str}")
    qr_dir = os.path.join(app.root_path, "static", "qrcodes")
    os.makedirs(qr_dir, exist_ok=True)
    qr.save(os.path.join(qr_dir, f"order_{order.id}.png"))

    db.session.commit()
    current_user.drinks_visited = False
    db.session.commit()

    flash("Order placed with COD! 🎉", "success")

    order_data = get_maker_order_data(order.id) 
    if order_data:
        socketio.emit('new_order', {'order': order_data}, namespace='/maker')

    return redirect(url_for("cart", celebration="1"))




    
socketio = SocketIO(app, cors_allowed_origins="*") 
@socketio.on('join')
def on_join(data):
    room = str(data.get('room'))
    if room:
        join_room(room)
        print(f"Socket {request.sid} joined order room: {room}")
        emit('status', {'msg': f'Joined order room: {room}'}, room=request.sid)


def notify_payment_verified(order_id):
    room_id = str(order_id)
    print(f"🚀 Notifying room {room_id}: Payment Verified.")
    socketio.emit(
        'payment_verified', 
        {'order_id': order_id, 'message': 'Payment confirmed. QR scanning activated.'}, 
        room=room_id
    )



@socketio.on('connect', namespace='/maker')
def handle_maker_connect():
    print(f"Maker connected: {request.sid}")
    emit('status', {'msg': 'Maker connection established'}, room=request.sid)

@socketio.on('disconnect', namespace='/maker')
def handle_maker_disconnect():
    print(f"Maker disconnected: {request.sid}")



@app.route("/payment/success")
@login_required
def payment_success():
    session_id = request.args.get("session_id")
    session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent.payment_method"])

    if session.payment_status == "paid":
        payment_intent = session.payment_intent
        transaction_id = payment_intent.id  
        payment_method_type = payment_intent.payment_method.type  

        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(ci.qty * next(size["price"] for size in get_product_data(ci.roll_id)["sizes"] if size["label"] == ci.size) for ci in cart_items)

        qr_code_str = str(uuid.uuid4())
        order = Order(
            user_id=current_user.id,
            total=total,
            qr_code=qr_code_str,
            placed_at=datetime.utcnow() + IST_OFFSET,
            created_at=datetime.utcnow() + IST_OFFSET,
            payment_status="paid",
            payment_method=payment_method_type,
            transaction_id=transaction_id
        )
        db.session.add(order)
        db.session.flush()

        for ci in cart_items:
            roll = get_product_data(ci.roll_id)
            price = next(size["price"] for size in roll["sizes"] if size["label"] == ci.size)
            db.session.add(OrderItem(
                order_id=order.id,
                roll_id=ci.roll_id,
                size=ci.size,
                qty=ci.qty,
                price_each=price,
                notes=ci.notes
            ))
            db.session.delete(ci)


        qr = qrcode.make(f"{qr_code_str}")
        qr_dir = os.path.join(app.root_path, "static", "qrcodes")
        os.makedirs(qr_dir, exist_ok=True)
        qr.save(os.path.join(qr_dir, f"order_{order.id}.png"))
        db.session.commit()

        flash("Order placed! 🎉", "success")
        current_user.drinks_visited = False
        db.session.commit()

        order_data = get_maker_order_data(order.id) 
        if order_data: 
            socketio.emit('new_order', {'order': order_data}, namespace='/maker')

        return redirect(url_for("cart", celebration="1"))
    
    flash("Payment not verified!", "error")
    return redirect(url_for("cart"))




@app.route("/payment/cancel")
@login_required
def payment_cancel():
    flash("Payment cancelled", "error")
    return redirect(url_for("cart"))




import io
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

@app.route("/orders/<int:order_id>/bill", methods=["GET"])
@login_required
def download_bill(order_id):
    order = Order.query.get_or_404(order_id)
    is_owner = str(order.user_id) == str(current_user.id) 
    is_admin = getattr(current_user, 'is_admin', False) 
    
    if not (is_owner or is_admin):
        flash("You are not authorized to view this bill. Access Denied.", "error")
        abort(403) 

    user = User.query.get(order.user_id) 
    if not user:
        flash("Customer data not found for this order.", "error")
        abort(404)
        
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 60

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, y, "BiteMyRoll")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.gray)
    c.drawString(50, y - 15, "Delicious Rolls & Beverages")
    c.setFillColor(colors.black)
    y -= 50

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Order ID: {order.id}")
    c.drawString(300, y, f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    y -= 20

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Customer: {user.username}")
    y -= 15
    c.drawString(50, y, f"Email: {user.email}")
    y -= 15
    phone_number = getattr(user, 'phone', 'N/A')
    c.drawString(50, y, f"Phone: {phone_number}")
    y -= 25
    
    if order.payment_method or getattr(order, 'transaction_id', None):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Payment Details")
        y -= 20

        c.setFont("Helvetica", 11)
        if order.payment_method:
            c.drawString(50, y, f"Method: {order.payment_method.capitalize()}")
            y -= 15
        if getattr(order, 'transaction_id', None):
            c.drawString(50, y, f"Transaction ID: {order.transaction_id}")
            y -= 25


    delivery_address_components = [
        getattr(user, 'street_road', None),
        getattr(user, 'area', None),
        getattr(user, 'pincode', None),
        getattr(user, 'state', None),
        getattr(user, 'country', None)
    ]
    delivery_address = ", ".join(filter(None, delivery_address_components))
    
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.darkblue)
    c.drawString(50, y, f"Delivery Location: {delivery_address}")
    c.setFillColor(colors.black)
    y -= 20

    if getattr(user, "pickup_point", None):
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(colors.darkgreen)
        c.drawString(50, y, f"Pickup Point: {user.pickup_point}")
        c.setFillColor(colors.black)
        y -= 20


    y -= 10

    c.setFillColor(colors.lightgrey)
    c.rect(50, y - 15, width - 100, 20, fill=True, stroke=False)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, y - 10, "Item")
    c.drawString(250, y - 10, "Qty")
    c.drawString(300, y - 10, "Price")
    c.drawString(380, y - 10, "Subtotal")
    y -= 35

    c.setFont("Helvetica", 10)
    total = 0
    for item in order.items:
        product = get_product_data(item.roll_id)
        subtotal = item.price_each * item.qty
        total += subtotal

        c.drawString(55, y, f"{product.get('name', 'Unknown Item')} ({item.size})")
        c.drawString(250, y, str(item.qty))
        c.drawString(300, y, f"₹{item.price_each:.2f}")
        c.drawString(380, y, f"₹{subtotal:.2f}")
        y -= 20

        if y < 100:
            c.showPage()
            y = height - 80

    c.setFont("Helvetica-Bold", 12)
    c.line(300, y - 5, 480, y - 5)
    y -= 20
    c.drawString(300, y, "Total:")
    c.drawString(380, y, f"₹{total:.2f}")
    y -= 40

    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.gray)
    c.drawCentredString(width / 2, 50, "Thank you for ordering with BiteMyRoll!")
    c.setFillColor(colors.black)

    c.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=False,
        download_name=f"bitemyroll_order_{order.id}.pdf",
        mimetype="application/pdf"
    )



@app.route("/cancel-order/<int:order_id>", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    db.session.delete(order)       
    db.session.commit()
    flash("Order cancelled.", "info")
    return redirect(url_for("orders"))

@app.route("/update-cart/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id):
    op   = request.form.get("op")         
    item = CartItem.query.filter_by(
        id=item_id, user_id=current_user.id
    ).first_or_404()

    if op == "inc":
        item.qty += 1

    elif op == "dec":
        item.qty -= 1
        if item.qty <= 0:
            db.session.delete(item)         

    db.session.commit()
    return redirect(url_for("cart"))

@app.route('/drinks')
@login_required
def drinksMenu():
    drinks = Product.query.filter_by(category="Beverage").all()

    if not current_user.drinks_visited:
        current_user.drinks_visited = True
        db.session.commit()

    return render_template('drinksMenu.html', drinks=drinks)




@app.route('/drinksDetail/<string:drink_key>')
def drinks_detail(drink_key):
    drink = Product.query.filter_by(name=drink_key, category="Beverage").first_or_404()
    return render_template('drinks_detail.html', roll=drink, roll_key=drink.name)


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
    current_user.lat = data.get("lat") if data.get("lat") is not None else None
    current_user.lon = data.get("lon") if data.get("lon") is not None else None

    db.session.commit()

    updated_address_data = {
        "user_id": current_user.id,
        "street_road": current_user.street_road,
        "ward": current_user.ward,
        "area": current_user.area,
        "pincode": current_user.pincode,
        "state": current_user.state,
        "country": current_user.country,
        "pickup_point": current_user.pickup_point,
        "lat": current_user.lat,
        "lon": current_user.lon
    }
    socketio.emit('location_update', updated_address_data, namespace='/')
    return jsonify(updated_address_data)


@app.context_processor
def inject_database():
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        rows, total = [], 0
        for ci in cart_items:
            roll = get_product_data(ci.roll_id)
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
    if current_user.is_admin not in [1, 2, 3]:
        abort(403)

    
    if current_user.is_admin == 1:
        orders = Order.query.filter(Order.status.in_(["Pending", "Processing","Ready for Delivered", "Out for Delivery"])).order_by(Order.placed_at.asc()).all()
    elif current_user.is_admin == 2:
        orders = Order.query.filter(Order.status.in_(["Pending", "Processing"])).order_by(Order.placed_at.asc()).all()
    elif current_user.is_admin == 3:
        orders = Order.query.filter(Order.status.in_(["Ready for Delivered", "Out for Delivery"])).order_by(Order.placed_at.asc()).all()

    order_data = []
    for order in orders:
        user = User.query.get(order.user_id)
        items = OrderItem.query.filter_by(order_id=order.id).all()

        item_list = []
        for item in items:
            try:
                product = get_product_data(item.roll_id)
            except:
                product = {}
            item_list.append({
                "name": product.get("name", item.roll_id),
                "size": item.size,
                "qty": item.qty,
                "price_each": item.price_each,
                "notes": item.notes
            })

        maker = User.query.get(order.prepared_by) if order.prepared_by else None
        delivery = User.query.get(order.delivered_by) if order.delivered_by else None

        order_data.append({
            "order_id": order.id,
            "placed_at": order.placed_at.strftime("%Y-%m-%d %H:%M"),
            "status": order.status,
            "total": order.total,
            "payment_method": order.payment_method,
            "transaction_id": order.transaction_id,
            "prepared_by": maker.email if maker else "—",
            "delivered_by": delivery.email if delivery else "—",
            "user": {
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "location": f"{user.street_road}, {user.area}, {user.pincode}, {user.state}, {user.country}",
                "pickup": user.pickup_point
            },
            "order_items": item_list
        })
    return render_template("admin/admin_orders.html", orders=order_data, title="All Orders")




@app.route("/admin/orders/history")
@login_required
def admin_order_history():
    if current_user.is_admin != 1:
        abort(403)

    delivered_cancelled_orders = Order.query.filter(
        Order.status.in_(["Delivered", "Cancelled"])
    ).order_by(Order.placed_at.desc()).all()

    order_data = []

    for order in delivered_cancelled_orders:
        user = User.query.get(order.user_id)
        items = OrderItem.query.filter_by(order_id=order.id).all()

        item_list = []
        for item in items:
            try:
                product = get_product_data(item.roll_id)
            except:
                product = {}

            item_list.append({
                "name": product.get("name", item.roll_id),
                "size": item.size,
                "qty": item.qty,
                "price_each": item.price_each,
                "notes": item.notes
            })
        maker = User.query.get(order.prepared_by) if order.prepared_by else None
        delivery = User.query.get(order.delivered_by) if order.delivered_by else None

        order_data.append({
            "order_id": order.id,
            "placed_at": order.placed_at.strftime("%Y-%m-%d %H:%M"),
            "status": order.status,
            "total": order.total,
            "payment_method": order.payment_method,
            "transaction_id": order.transaction_id,
            "prepared_by": maker.email if maker else "—",
            "delivered_by": delivery.email if delivery else "—",
            "user": {
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "location": f"{user.street_road}, {user.area}, {user.pincode}, {user.state}, {user.country}",
                "pickup": user.pickup_point
            },
            "order_items": item_list
        })

    return render_template("admin/admin_orders.html", orders=order_data, title="Order History")



@app.route("/admin/update_status/<int:order_id>", methods=["POST"])
@login_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)

  
    if not current_user.is_authenticated or current_user.is_admin not in [1, 2, 3]:
        abort(403)

   
    action = request.form.get("action")
    new_status = request.form.get("status")

    if current_user.is_admin in [1, 2]:
        if action == "update" and new_status:
            order.status = new_status
            db.session.commit()
            flash("Order status updated.", "success")
        elif action == "cancel":
            order.status = "Cancelled"
            db.session.commit()
            flash("Order cancelled.", "info")
        else:
            flash("Unknown action.", "error")

    elif current_user.is_admin == 3:
        
        if new_status in ["Out for Delivery", "Delivered"]:
            order.status = new_status
            db.session.commit()
            flash(f"Marked as {new_status}.", "success")
        else:
            flash("Invalid status for delivery.", "error")

    return redirect(request.referrer or url_for("admin_orders"))



class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())



@app.route('/contact', methods=['GET', 'POST'])
def contact_form():
    form = ContactForm()
    if request.method == 'GET' and current_user.is_authenticated:
        form.email.data = current_user.email

    if form.validate_on_submit():
        new_msg = ContactMessage(
            username=form.username.data,
            email=form.email.data,
            category=form.category.data,
            message=form.message.data
        )
        db.session.add(new_msg)
        db.session.commit()
        flash('Thank you! Your message has been received.', 'success')
        return redirect(url_for('contact_form'))

    return render_template('contact.html', form=form)


@app.route('/admin/messages')
@login_required
def admin_messages():
    if current_user.is_admin != 1:
        abort(403)  

    messages = ContactMessage.query.order_by(ContactMessage.timestamp.desc()).all()
    return render_template('admin/admin_messages.html', messages=messages)


@app.route('/admin/messages/delete', methods=['POST'])
@login_required
def delete_selected_messages():
    if current_user.is_admin != 1:
        abort(403)

    ids = request.form.getlist('message_ids')
    if ids:
        ContactMessage.query.filter(ContactMessage.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f"{len(ids)} message(s) deleted successfully.", 'success')
    else:
        flash("No messages selected.", 'warning')
    return redirect(url_for('admin_messages'))


@app.route('/admin/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.is_admin != 1:
        abort(403)

    form = CreateUserForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user:
            user.username = form.username.data
            user.is_admin = int(form.role.data)
            if form.password.data: 
                user.set_password(form.password.data)
            flash('User updated successfully!', 'info')
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                is_admin=int(form.role.data)
            )
            user.set_password(form.password.data)
            db.session.add(user)
            flash('User created successfully!', 'success')

        db.session.commit()
        return redirect(url_for('admin_orders'))

    return render_template('admin/create_user.html', form=form)


from itsdangerous import URLSafeTimedSerializer
from flask import current_app

app.config["SECRET_KEY"] = "5a11f4cdd0e846bfb486df9e4ec9ac88f49f21e6a370a1f3e316d40b245b2c7e"

def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset-salt')

def verify_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except Exception:
        return None
    return email


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm() 
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = generate_reset_token(user.email)
            reset_link = url_for('reset_password', token=token, _external=True)

            
            print(f"""
                to=user.email,
                subject="Reset Your BiteMyRoll Password",
                body="Hi {user},\n\nClick below to reset your password:\n{reset_link}\n\nThis link will expire in 1 hour."""
            )
            send_reset_email(user=user,token=reset_link)
            print("Reset link (for testing):", reset_link)
        flash("If the email exists, a reset link has been sent.", "info")
        return redirect(url_for('login'))
    return render_template('forgot_password.html', form=form)


from flask_login import login_user

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash('Invalid or expired link.', 'danger')
        return redirect(url_for('login'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(form.password.data)  
            db.session.commit()
            login_user(user) 
            flash('Your password has been reset. You are now logged in.', 'success')
            return redirect(url_for('home'))  
    return render_template('reset_password.html', form=form)


@app.route('/admin/dashboard')
@login_required
def dashboard():
    if current_user.is_admin != 1:
        abort(403)

    return render_template('admin/admin_dashboard.html')



from flask import send_from_directory
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = BASE_DIR / "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/admin/detail/<type>')
@login_required
def admin_detail(type):
    if current_user.is_admin != 1:
        abort(403)
    roll = get_product_data(type)
    return render_template('admin/admin_roll_detail.html',
                           roll=roll,
                           title=f"Edit {roll['name']}",
                           roll_key=type)

@app.route('/admin/update_product/<string:roll_key>/<string:type>', methods=["POST"])
@login_required
def admin_update_product(roll_key, type):
    if current_user.is_admin != 1:
        abort(403)

    product = Product.query.filter_by(name=roll_key).first_or_404()

    old_name = product.name

    new_name = request.form.get("name", product.name)
    product.name = new_name
    product.diet = request.form.get("diet", product.diet)
    product.description = request.form.get("desc", product.description)

    if "sizes" in request.form:
        import json
        sizes = json.loads(request.form["sizes"])
        ProductSize.query.filter_by(product_id=product.id).delete()
        for s in sizes:
            db.session.add(ProductSize(
                product_id=product.id,
                label=s["label"],
                price=s["price"],
                is_available=s.get("available", True)
            ))

    if "image" in request.files:
        img = request.files["image"]
        if img.filename:
            ext = os.path.splitext(img.filename)[1].lower()
            filename = secure_filename(new_name.replace(" ", "_")) + ext
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            img.save(filepath)
            product.image = f"uploads/{filename}"

    if old_name != new_name:
        CartItem.query.filter_by(roll_id=old_name).update({CartItem.roll_id: new_name})
        OrderItem.query.filter_by(roll_id=old_name).update({OrderItem.roll_id: new_name})

    db.session.commit()

    new_path = f"/admin/detail/{product.name}"
    print(f"[DEBUG] Redirect path should be: {new_path}")

    if type == 'drink':
        return jsonify({
            "status": "success",
            "redirect_url": f"/admin/drinksDetail/{product.name}",
            "new_image_url": url_for("static", filename=product.image)
        })
    return jsonify({
        "status": "success",
        "redirect_url": new_path,
        "new_image_url": url_for("static", filename=product.image)
    })


@app.route("/admin/toggle_product/<int:product_id>", methods=["POST"])
@login_required
def toggle_product_availability(product_id):
    if current_user.is_admin != 1:
        abort(403)

    product = Product.query.get_or_404(product_id)
    is_available = request.form.get("is_available") == "1"

    for s in product.sizes:
        s.is_available = is_available

    db.session.commit()
    flash(f"{product.name} marked as {'Available' if is_available else 'Unavailable'}.", "success")
    return redirect(url_for("menu"))



@app.route('/admin/add_product', methods=["GET", "POST"])
@login_required
def admin_add_product():
    if current_user.is_admin != 1:
        abort(403)

    if request.method == "POST":
        name = request.form.get("name").strip()

        existing = Product.query.filter_by(name=name).first()
        if existing:
            flash("A product with this name already exists!", "error")
            return redirect(url_for("admin_add_product"))

        diet = request.form.get("diet")
        desc = request.form.get("desc")

        product = Product(name=name, category="Roll", diet=diet, description=desc)

        img = request.files.get("image")
        if img and img.filename:
            ext = os.path.splitext(img.filename)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                ext = ".png"   
            safe_name = secure_filename(name.replace(" ", "_"))
            filename = f"{safe_name}{ext}"

            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            img.save(filepath)

            product.image = f"uploads/{filename}"
            print(f"[DEBUG] Saved image OK → {filepath}")
        else:
            product.image = "uploads/placeholder.png"

        db.session.add(product)
        db.session.flush()

        labels = request.form.getlist("size_label[]")
        prices = request.form.getlist("size_price[]")
        all_available = request.form.get("all_available") == "1"

        for i in range(len(labels)):
            label = labels[i]
            price = float(prices[i]) if prices[i] else 0.0

            db.session.add(ProductSize(
                product_id=product.id,
                label=label,
                price=price,
                is_available=all_available   
            ))

        db.session.commit()
        flash("Product added successfully!", "success")
        return redirect(url_for("menu"))

    return render_template("admin/add_product.html")



@app.route('/admin/add_drinks_product', methods=["GET", "POST"])
@login_required
def admin_add_drink():
    if current_user.is_admin != 1:
        abort(403)

    if request.method == "POST":
        name = request.form.get("name").strip()

        existing = Product.query.filter_by(name=name).first()
        if existing:
            flash("A product with this name already exists!", "error")
            return redirect(url_for("admin_add_drink"))

        desc = request.form.get("desc")

        product = Product(name=name, category="Beverage", diet=None, description=desc)

        img = request.files.get("image")
        if img and img.filename:
            ext = os.path.splitext(img.filename)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                ext = ".png"
            safe_name = secure_filename(name.replace(" ", "_"))
            filename = f"{safe_name}{ext}"

            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            img.save(filepath)

            product.image = f"uploads/{filename}"
        else:
            product.image = "uploads/placeholder.png"

        db.session.add(product)
        db.session.flush()

      
        labels = request.form.getlist("size_label[]")
        prices = request.form.getlist("size_price[]")
        all_available = request.form.get("all_available") == "1"

        for i in range(len(labels)):
            label = labels[i]
            price = float(prices[i]) if prices[i] else 0.0

            db.session.add(ProductSize(
                product_id=product.id,
                label=label,
                price=price,
                is_available=all_available  
            ))



        db.session.commit()
        flash("Drink added successfully!", "success")
        return redirect(url_for("drinksMenu"))

    return render_template("admin/add_drinks_product.html")



@app.route("/admin/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        return redirect(url_for("menu"))

    product = Product.query.get_or_404(product_id)

    for size in product.sizes:
        db.session.delete(size)

    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully!", "success")
    return redirect(url_for("menu"))


@app.route("/admin/delete_size/<int:size_id>", methods=["POST"])
@login_required
def delete_size(size_id):
    if not current_user.is_admin:
        return redirect(url_for("menu"))

    size = ProductSize.query.get_or_404(size_id)   
    db.session.delete(size)
    db.session.commit()
    flash("Size deleted successfully!", "success")
    return redirect(request.referrer or url_for("menu"))



@app.route('/admin/drinksDetail/<string:drink_key>')
@login_required
def admin_drinks_detail(drink_key):
    if current_user.is_admin != 1:
        abort(403)
    drink = Product.query.filter_by(name=drink_key, category="Beverage").first_or_404()
    return render_template(
        'admin/admin_drinks_detail.html',
        roll=drink,
        roll_key=drink.name,
        title=f"Edit {drink.name}"
    )



@app.route('/admin/drinks/toggle/<int:drink_id>', methods=["POST"])
@login_required
def toggle_drink_availability(drink_id):
    if current_user.is_admin != 1:
        abort(403)
    drink = Product.query.get_or_404(drink_id)
    has_available = any(s.is_available for s in drink.sizes)
    for s in drink.sizes:
        s.is_available = not has_available
    db.session.commit()
    return redirect(url_for("drinksMenu"))


@app.route('/admin/drinks/delete/<int:drink_id>', methods=["POST"])
@login_required
def delete_drink(drink_id):
    if current_user.is_admin != 1:
        abort(403)
    drink = Product.query.get_or_404(drink_id)
    db.session.delete(drink)
    db.session.commit()
    return redirect(url_for("drinksMenu"))


import requests

def send_reset_email(user, token):
    base_url = "https://script.google.com/macros/s/AKfycbwCg3EG4kq0WyhNfX-dsrJRF35V00S5LSLrqu6raKtxi6gs8XPyznXDWw-gUSc0tOFQ/exec"

    payload = {
        "forget": "1",
        "user": user.email,
        "token": token
    }

    response = requests.post(base_url, data=payload)
    print("Email API response:", response.text)





app.config["GOOGLE_OAUTH_CLIENT_ID"] = "444014278417-1qs2v40esh9jn4g35jfdber47773n58v.apps.googleusercontent.com"
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = "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"

from flask_dance.contrib.google import make_google_blueprint, google

google_bp = make_google_blueprint(
    client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
    client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ],
)

app.register_blueprint(google_bp, url_prefix="/login")

from flask_dance.consumer import oauth_authorized
from flask import redirect, url_for
from flask_login import login_user
from sqlalchemy.orm.exc import NoResultFound

@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    if not token:
        flash("Failed to log in with Google.", category="error")
        return False

    resp = blueprint.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", category="error")
        return False

    user_info = resp.json()
    email = user_info["email"]

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            username=user_info.get("name", email.split("@")[0]),
            pw_hash=""
        )
        db.session.add(user)
        db.session.commit()

    login_user(user, remember=True)
    if not user.phone:
        return redirect(url_for("add_phone", order="true"))

    flash("Logged in successfully!", "success")
    return redirect(url_for("home"))
    return False 





app.config["GITHUB_OAUTH_CLIENT_ID"] = "Ov23li0PsCxqzaPuKuTd"
app.config["GITHUB_OAUTH_CLIENT_SECRET"] = "a9d5a2a3a4a8d664d791096d5660c3414db9e91a"

from flask_dance.contrib.github import make_github_blueprint, github

github_bp = make_github_blueprint(
    client_id=app.config["GITHUB_OAUTH_CLIENT_ID"],
    client_secret=app.config["GITHUB_OAUTH_CLIENT_SECRET"],
    scope="user:email",
    redirect_to="home"
)


app.register_blueprint(github_bp, url_prefix="/login")

@oauth_authorized.connect_via(github_bp)
def github_logged_in(blueprint, token):
    if not token:
        flash("Failed to log in with GitHub.", category="error")
        return False

    resp = blueprint.session.get("/user")
    if not resp.ok:
        flash("Failed to fetch user info from GitHub.", category="error")
        return False

    github_info = resp.json()
    email = github_info.get("email")

    if not email:
        emails_resp = blueprint.session.get("/user/emails")
        if emails_resp.ok:
            emails = emails_resp.json()
            primary_emails = [e["email"] for e in emails if e.get("primary")]
            if primary_emails:
                email = primary_emails[0]

    if not email:
        flash("GitHub account has no public email. Please add an email to your GitHub profile.", "error")
        return False

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            username=github_info.get("login", email.split("@")[0]),
            pw_hash=""
        )
        db.session.add(user)
        db.session.commit()

    login_user(user, remember=True)
    flash("Logged in successfully with GitHub!", "success")
    return redirect(url_for("home"))



@app.route("/add_phone", methods=["GET", "POST"])
@login_required
def add_phone():
    if request.method == "POST":
        phone = request.form.get("phone")
        if phone:
            current_user.phone = phone
            db.session.commit()
            flash("Phone number saved!", "success")

            if request.args.get("order", "false").lower() == "true":
                return redirect(url_for("cart"))
            return redirect(url_for("menu"))
        else:
            flash("You can add phone number later in your profile.", "info")
            return redirect(url_for("menu"))

    order_flag = request.args.get("order", "false").lower() == "true"
    return render_template("add_phone.html", order=order_flag)



import stripe
from flask import jsonify

app.config["STRIPE_SECRET_KEY"] = "sk_test_51S4MaPJxbaHWh73eWlw79jWhh0kqZ1BcYVSXyx0ZgWQCJDYSnrBRl6LFlHPWxC791lEkP9GAjRf7PjuW9fqtm4a8000UtYEo5Y"
app.config["STRIPE_PUBLISHABLE_KEY"] = "pk_test_51S4MaPJxbaHWh73eGGO1GODC79dVb1ZJoMhdh8nQNMqgxAWt4qDyz0NgdCjywTPhlZrg3r928TKTYOscrCq83WrJ00wHsCXhAL"

stripe.api_key = app.config["STRIPE_SECRET_KEY"]


@app.route("/maker/orders")
@login_required
def maker_orders():
    if current_user.is_admin != 2:
        abort(403)

    active_order = Order.query.filter_by(prepared_by=current_user.id).filter(Order.status.in_(["Processing"])).first()
    if active_order:
        return render_template("staff/maker_active.html", order=active_order)

    orders = Order.query.filter_by(status="Pending").order_by(Order.placed_at.asc()).all()
    return render_template("staff/maker_orders.html", orders=orders)


def get_maker_order_data(order_id):
    order = Order.query.get(order_id)
    if not order:
        return None
    item_rows = OrderItem.query.filter_by(order_id=order.id).all()
    
    items_detail = []
    for i in item_rows:
        product = get_product_data(i.roll_id) 
        items_detail.append({
            "name": product["name"],
            "size": i.size,
            "qty": i.qty,
            "price_each": float(i.price_each),
            "notes": i.notes
        })
    customer = User.query.get(order.user_id)
    
    return {
        'id': order.id,
        'placed_at': order.placed_at.strftime("%Y-%m-%d %H:%M:%S"), 
        'total': float(order.total), 
        'payment_status': order.payment_status,
        'payment_method': order.payment_method,
        'customer_name': customer.username if customer else 'N/A',
        'items': items_detail
    }


@app.route("/maker/pick/<int:order_id>", methods=["POST"])
@login_required
def maker_pick(order_id):
    if current_user.is_admin != 2:
        abort(403)

    order = Order.query.get_or_404(order_id)
    if order.status != "Pending" or order.prepared_by:
        flash("Order already taken.", "error")
        return redirect(url_for("maker_orders"))

    order.status = "Processing"
    order.prepared_by = current_user.id
    db.session.commit()
    socketio.emit(
        'order_picked', 
        {'order_id': order_id, 'maker_id': current_user.id, 'maker_name': current_user.username}, 
        namespace='/maker',
    )
    flash("You started preparing the order.", "success")
    return redirect(url_for("maker_orders"))


def order_to_dict(order):
    return {
        'id': order.id,
        'total': order.total,
        'payment_status': order.payment_status,
        'placed_at': str(order.placed_at.strftime('%Y-%m-%d %H:%M:%S')), 
    }

def user_to_dict(user):
    return {
        'id': user.id,
        'email': user.email,
        'phone': user.phone,
        'username': user.username,
        'street_road': user.street_road,
        'ward': user.ward,
        'area': user.area,
        'pincode': user.pincode,
        'state': user.state,
        'country': user.country,
        'pickup_point': user.pickup_point
    }


@app.route("/maker/ready/<int:order_id>", methods=["POST"])
@login_required
def maker_ready(order_id):
    if current_user.is_admin != 2:
        abort(403)

    order = Order.query.get_or_404(order_id)
    if order.prepared_by != current_user.id or order.status != "Processing":
        flash("You cannot update this order.", "error")
        return redirect(url_for("maker_orders"))

    order.status = "Ready for Delivered"
    order_data = order_to_dict(order)
    customer = User.query.get_or_404(order.user_id)

    socketio.emit('order_ready_for_delivery', {
        "order": order_data,  
        "customer": user_to_dict(customer) 
    }, namespace='/')
    db.session.commit()
    flash("Order marked ready for delivery.", "success")
    return redirect(url_for("maker_orders"))





@app.route("/delivery/orders")
@login_required
def delivery_orders():
    if current_user.is_admin != 3:
        abort(403)
    active_order = Order.query.filter_by(delivered_by=current_user.id).filter(Order.status.in_(["Out for Delivery"])).first()
    if active_order:
        customer = User.query.get_or_404(active_order.user_id)
        return render_template("staff/delivery_active.html", order=active_order, user=customer)
    orders = Order.query.filter_by(status="Ready for Delivered").order_by(Order.placed_at.asc()).all()
    available_orders_with_details = []
    for order in orders:
        customer = db.session.get(User, order.user_id) 
        
        available_orders_with_details.append({
            'order': order,
            'customer': customer,
            'customer_id': order.user_id
        })
    return render_template("staff/delivery_orders.html", available_orders=available_orders_with_details )


@app.route("/delivery/pick/<int:order_id>", methods=["POST"])
@login_required
def delivery_pick(order_id):
    if current_user.is_admin != 3:
        abort(403)

    order = Order.query.get_or_404(order_id)
    if order.status != "Ready for Delivered" or order.delivered_by:
        flash("Order already taken.", "error")
        return redirect(url_for("delivery_orders"))

    order.status = "Out for Delivery"
    order.delivered_by = current_user.id
    db.session.commit()

    socketio.emit(
        'order_taken', 
        {'order_id': order_id}, 
        namespace='/' 
    )
    
    flash("You picked the order for delivery.", "success")
    return redirect(url_for("delivery_orders"))


@app.route("/delivery/delivered/<int:order_id>", methods=["GET", "POST"])
@login_required
def delivery_delivered(order_id):
    if current_user.is_admin != 3:
        abort(403)

    order = Order.query.get_or_404(order_id)
    if order.delivered_by != current_user.id:
        flash("You cannot update this order.", "error")
        return redirect(url_for("delivery_orders"))

    order.status = "Delivered"
    db.session.commit()
    flash("Order marked delivered ", "success")
    return redirect(url_for("delivery_orders"))


@app.route("/delivery/verify_and_deliver/<int:order_id>", methods=["POST"])
@login_required
def delivery_verify_and_deliver(order_id):
    if current_user.is_admin != 3:
        return jsonify({"success": False, "message": "Access denied."}), 403

    order = Order.query.get_or_404(order_id)
    
    if order.delivered_by != current_user.id or order.status != "Out for Delivery":
        return jsonify({"success": False, "message": "Cannot update this order. Status is not 'Out for Delivery'."}), 400

    data = request.get_json()
    scanned_qr_code = data.get('qr_code_value')

    if not scanned_qr_code:
        return jsonify({"success": False, "message": "No QR code value received."}), 400

    if scanned_qr_code != order.qr_code:
        return jsonify({"success": False, "message": "Verification FAILED: QR Code Mismatch! Order not verified."}), 400

    order.status = "Delivered"
    db.session.commit()

    flash(f"Order #{order.id} marked delivered ", "success")
    
    return jsonify({"success": True, "message": "Order verified and marked as Delivered."})



from decimal import Decimal, InvalidOperation 
import traceback 

@app.route("/delivery/pay_by_cash/<int:order_id>", methods=["POST"])
@login_required
def pay_by_cash(order_id):
    if current_user.is_admin != 3:
        abort(403)

    order = Order.query.get_or_404(order_id)
    if order.delivered_by != current_user.id or order.status != "Out for Delivery" or order.payment_status != "not paid":
        flash("Cannot process cash payment. Order is not assigned to you, not out for delivery, or already paid.", "error")
        return redirect(url_for("delivery_active", order_id=order_id))

    try:
        order_total = Decimal(str(order.total)) 
        if order_total < 0:
            raise ValueError("Order total cannot be negative during payment processing.")
        if current_user.cash_due_by_delivery_boy is None:
            current_user.cash_due_by_delivery_boy = Decimal('0.00')
        order.payment_status = 'paid'
        order.status = 'Delivered'
        current_user.cash_due_by_delivery_boy += order_total
        db.session.commit()
        flash(f"Order #{order_id} marked paid by CASH. Your cash-due balance is increased by ₹{order_total:.2f}.", "success")
        
    except InvalidOperation:
        db.session.rollback()
        flash("Error: The order total value is not a valid number.", "error")
        return redirect(url_for("delivery_active", order_id=order_id))
        
    except ValueError as e:
        db.session.rollback()
        print(f"ValueError in pay_by_cash: {e}")
        flash(f"Validation Error: {e}", "error")
        return redirect(url_for("delivery_active", order_id=order_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"CRITICAL ERROR in pay_by_cash for order {order_id}: {e}")
        traceback.print_exc()
        flash(f"A critical system error occurred while processing payment.", "error")
        return redirect(url_for("delivery_active", order_id=order_id))
        
    return redirect(url_for('delivery_delivered', order_id=order_id))



@app.route("/payment/order-paid-confirmation/<int:order_id>")
def order_paid_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("customer_payment_success.html", order=order, title="Payment Successful")



@app.route("/delivery/payment/success/<int:order_id>", methods=["GET"])
def delivery_payment_success(order_id):
    order = Order.query.get_or_404(order_id)
    session_id = request.args.get("session_id")
    customer_redirect_url = url_for('order_paid_confirmation', order_id=order_id)
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == "paid":
            if order.status != 'Delivered':
                order.payment_status = 'paid'
                order.status = 'Delivered' 
                order.payment_method = 'Online / Stripe'
                order.transaction_id = session_id
                db.session.commit()
                socketio.emit(
                    'order_paid', 
                    {'order_id': order_id},
                    namespace='/' 
                )
                socketio.emit('payment_status_update', {
                    "order_id": order.id,
                    "status": 'Paid'
                }, namespace='/')
                flash(f"Order #{order_id} successfully paid online and marked **DELIVERED**! The order is complete.", "success")
        return redirect(customer_redirect_url)


    except stripe.error.StripeError as e:
        print(f"Stripe Error on success URL: {e}")
        return redirect(url_for('home')) 
        
    except Exception as e:
        print(f"Unexpected Error in delivery_payment_success: {e}")
        return redirect(url_for('home'))
    


@app.route("/delivery/generate_payment_link/<int:order_id>", methods=["POST"])
@login_required
def generate_payment_link(order_id):
    if current_user.is_admin != 3:
        return jsonify({"message": "Forbidden: Only delivery staff can generate payment links."}), 403

    try:
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({"message": "Order not found."}), 404
        ALLOWED_STATUSES = ["Ready for Delivered", "Out for Delivery"]
        if order.status not in ALLOWED_STATUSES:
            return jsonify({"message": f"Invalid order status ({order.status}) for generating payment link."}), 400

        if order.payment_status == 'paid':
            return jsonify({"message": "Payment is already marked as paid."}), 400
        amount_in_paise = int(order.total * 100)
        success_url = url_for("delivery_payment_success", order_id=order.id, _external=True)
        cancel_url = url_for("delivery_delivered", order_id=order.id, _external=True)

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {"name": f"BiteMyRoll Order #{order.id}"},
                    "unit_amount": amount_in_paise,
                },
                "quantity": 1,
            }],
            mode="payment",
            client_reference_id=str(order.id),
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}", 
            cancel_url=cancel_url,
        )
        stripe_payment_url = session.url
        TINYURL_API_ENDPOINT = "http://tinyurl.com/api-create.php"
        final_payment_url = stripe_payment_url 

        try:
            shortening_response = requests.get(
                TINYURL_API_ENDPOINT,
                params={'url': stripe_payment_url},
                timeout=3
            )
            if shortening_response.status_code == 200 and not shortening_response.text.startswith('Error'):
                shortened_url = shortening_response.text.strip()
                if shortened_url.startswith('http'):
                    final_payment_url = shortened_url
                    order.short_payment_url = final_payment_url
                    db.session.commit()
                    
                    print(f"Stripe URL shortened successfully via TinyURL: {final_payment_url}")
                else:
                    print(f"TinyURL returned invalid URL. Using original Stripe URL.")
            else:
                print(f"TinyURL API failed (Status {shortening_response.status_code}, Text: {shortening_response.text[:50]}...). Using original Stripe URL.")
                
        except requests.RequestException as e:
            print(f"Network error during TinyURL shortening: {e}. Using original Stripe URL.")
        return jsonify({"message": "Payment link generated.", "url": final_payment_url}), 200

    except stripe.error.StripeError as e:
        print(f"Stripe Error: {e}")
        return jsonify({"message": f"Stripe integration failed: {str(e)}"}), 500
    except Exception as e:
        print(f"Unexpected Error in generate_payment_link: {e}")
        return jsonify({"message": "An unexpected server error occurred."}), 500

@app.route('/api/pay-existing-order', methods=['POST'])
@login_required
def api_pay_existing_order():
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({"message": "Missing order ID."}), 400

    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        return jsonify({"message": "Order not found or access denied."}), 404
        
    if order.payment_status == 'paid':
        return jsonify({"message": "Order is already paid."}), 400

    try:
        total = order.total
        amount_in_paise = int(total * 100)

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {"name": f"BiteMyRoll Order #{order_id}"},
                    "unit_amount": amount_in_paise,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=url_for("payment_success_existing", order_id=order_id, _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("payment_cancel", _external=True),
            metadata={'order_id': order_id} 
        )

        final_payment_url = session.url
        return jsonify({"message": "Payment link generated.", "url": final_payment_url}), 200

    except stripe.error.StripeError as e:
        print(f"Stripe Error: {e}")
        return jsonify({"message": f"Stripe integration failed: {str(e)}"}), 500
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return jsonify({"message": "An unexpected server error occurred."}), 500
    


@app.route("/payment/success-existing/<int:order_id>")
def payment_success_existing(order_id):
    session_id = request.args.get("session_id")
    
    if not session_id:
        flash("Payment session ID is missing.", "error")
        return redirect(url_for("orders") or url_for("index"))

    try:
        session = stripe.checkout.Session.retrieve(
            session_id, 
            expand=["payment_intent", "line_items"] 
        )
        order = db.session.get(Order, order_id)
        
        if not order:
            flash("Error: Order not found in our database.", "error")
            return redirect(url_for("orders") or url_for("index"))
        print(f"DEBUG: Order #{order_id} - Stripe Session Status: {session.payment_status}")

        if session.payment_status == "paid":
            if session.payment_intent and session.payment_intent.status == "succeeded":
                order.payment_status = "paid"
                payment_method_type = session.payment_intent.payment_method_types[0] if session.payment_intent.payment_method_types else 'card'
                
                order.payment_method = payment_method_type
                order.transaction_id = session.payment_intent.id
                db.session.commit()
                print(f"SUCCESS: Order #{order_id} marked as PAID. Transaction ID: {order.transaction_id}")
                if 'notify_payment_verified' in globals():
                    socketio.emit(
                        'order_paid', 
                        {'order_id': order_id},
                        namespace='/'
                    )
                    socketio.emit('payment_status_update', {
                        "order_id": order.id,
                        "status": 'Paid'
                    }, namespace='/')
                    print(f"SUCCESS: WebSocket notification sent for Order #{order_id}")
                
                flash(f"Payment for Order #{order_id} confirmed! 🎉", "success")
                return redirect(url_for("orders"))
            else:
                print(f"WARNING: Order #{order_id} - Payment status is 'paid' but intent status is '{session.payment_intent.status}'. Not marking as paid yet.")
                flash("Payment is currently processing. Please check order status shortly.", "warning")
                return redirect(url_for("orders"))
        flash("Payment not successfully verified by Stripe. Status: " + session.payment_status, "error")
        return redirect(url_for("orders"))

    except stripe.error.StripeError as e:
        flash(f"Payment verification failed due to Stripe error: {str(e)}", "error")
        print(f"Stripe Error in payment_success_existing: {e}")
        return redirect(url_for("orders") or url_for("index"))
        
    except Exception as e:
        flash("An unexpected error occurred during payment finalization.", "error")
        import traceback
        print(f"CRITICAL ERROR in payment_success_existing: {e}")
        traceback.print_exc()
        db.session.rollback() 
        return redirect(url_for("orders") or url_for("index"))

@app.route("/delivery/pay_due", methods=["GET"])
@login_required
def delivery_pay_due():
    if current_user.is_admin != 3:
        flash("Access denied. You are not authorized to use this feature.", "error")
        return redirect(url_for('home'))
    amount_due = current_user.cash_due_by_delivery_boy if current_user.cash_due_by_delivery_boy is not None else Decimal('0.00')
    if amount_due <= Decimal('0.01'): 
        flash("You have no outstanding cash due to pay at this time. Thank you!", "info")
        return redirect(url_for('delivery_dashboard')) 

    try:
        amount_in_paise = int(amount_due * 100)
        base_domain = request.url_root.rstrip('/')

        # URL for successful payment
        success_url = base_domain + url_for("delivery_pay_due_success") + "?session_id={CHECKOUT_SESSION_ID}"
        cancel_url = base_domain + url_for("delivery_dashboard") 

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {"name": f"CoD Due Payment - User {current_user.id}"},
                    "unit_amount": amount_in_paise,
                },
                "quantity": 1,
            }],
            mode="payment",
            client_reference_id=f"DUE_PAY_{current_user.id}",
            success_url=success_url, 
            cancel_url=cancel_url,
        )
        return redirect(session.url, code=303)

    except stripe.error.StripeError as e:
        print(f"Stripe Error in delivery_pay_due: {e}")
        flash(f"Payment initiation failed due to Stripe error: {str(e)}", "error")
        return redirect(url_for('delivery_dashboard'))
    except Exception as e:
        print(f"Unexpected Error in delivery_pay_due: {e}")
        flash("An unexpected server error occurred during payment initiation.", "error")
        return redirect(url_for('delivery_dashboard'))


@app.route("/delivery/pay_due/success", methods=["GET"])
@login_required
def delivery_pay_due_success():
    if current_user.is_admin != 3:
        return redirect(url_for('home'))

    session_id = request.args.get("session_id")
    if not session_id:
        flash("Payment verification failed: Missing session ID.", "error")
        return redirect(url_for('delivery_dashboard'))

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            
            expected_ref = f"DUE_PAY_{current_user.id}"
            
            if session.client_reference_id != expected_ref:
                 flash("Security alert: Mismatched payment reference.", "error")
                 return redirect(url_for('delivery_dashboard'))
            paid_amount = session.amount_total / 100.0
            current_user.cash_due_by_delivery_boy -= Decimal(str(paid_amount))
            if current_user.cash_due_by_delivery_boy < Decimal('0.00'):
                current_user.cash_due_by_delivery_boy = Decimal('0.00')
            
            db.session.commit()
            
            flash(f"Success! Your CoD due of ₹{paid_amount:,.2f} has been paid. Your remaining due is ₹{current_user.cash_due_by_delivery_boy:,.2f}.", "success")
            
            return redirect(url_for('delivery_dashboard'))

        else:
            flash(f"Payment was not finalized. Status: {session.payment_status}", "warning")
            return redirect(url_for('delivery_dashboard'))

    except stripe.error.StripeError as e:
        print(f"Stripe Error in delivery_pay_due_success: {e}")
        flash(f"Payment verification failed due to Stripe error: {str(e)}", "error")
        return redirect(url_for('delivery_dashboard'))
    except Exception as e:
        traceback.print_exc()
        flash("An unexpected server error occurred during payment finalization.", "error")
        db.session.rollback()
        return redirect(url_for('delivery_dashboard'))

def get_today_start_utc(offset):
    now_utc = datetime.utcnow()
    now_offset = now_utc + offset
    today_start_offset = datetime.combine(now_offset.date(), datetime.min.time())
    today_start_utc = today_start_offset - offset
    return today_start_utc


def get_delivery_dashboard_data(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return {} 
    today_start_utc = get_today_start_utc(IST_OFFSET)
    deliveries_today = db.session.query(func.count(Order.id)).filter(
        Order.delivered_by == user_id,
        Order.status == 'Delivered', 
        Order.created_at >= today_start_utc 
    ).scalar()
    total_commission_today = (deliveries_today * Decimal('30')).quantize(Decimal('0.01'))
    pending_orders = db.session.query(func.count(Order.id)).filter(
        Order.delivered_by == user_id,
        Order.status.in_(['Ready for Delivered', 'Out for Delivery']) 
    ).scalar()
    user_hash = hash(user_id) % 100 
    avg_delivery_time = 18 + (user_hash % 3)
    
    return {
        "deliveries_today": deliveries_today,
        "total_commission_today": total_commission_today,
        "avg_delivery_time": avg_delivery_time,
        "pending_orders": pending_orders,
        "rating": 4.5 + (user_hash % 5) / 100.0,
        "co_due": user.cash_due_by_delivery_boy if user.cash_due_by_delivery_boy is not None else Decimal('0.00')
    }

@app.route("/delivery/dashboard")
@login_required
def delivery_dashboard():
    if current_user.is_admin != 3:
        flash("Access denied. You are not authorized to view the Delivery Dashboard.", "error")
        return redirect(url_for('home'))
    dashboard_data = get_delivery_dashboard_data(current_user.id)
    return render_template("staff/delivery_dashboard.html", data=dashboard_data)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("Starting server with SocketIO...")
    socketio.run(
        app, 
        debug=True, 
        host='0.0.0.0', 
        port=5000,
        ssl_context='adhoc'
    )

#ssl_context='adhoc'
