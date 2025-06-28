"""staff_routes.py – Admin/staff Blueprint separated from app.py without circular imports.

This module defines:
* admin_bp – Blueprint mounted at /admin
* admin_required – decorator that allows only users with is_admin=True
* /orders – list all orders with customer details
* /order-delivered/<id> – mark an order as delivered

All heavy imports (db, models, ROLLS_DATA) are **inside the view functions**
to avoid circular dependencies when app.py imports this blueprint.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from functools import wraps

admin_bp = Blueprint("admin", __name__, template_folder="templates",url_prefix="/admin")

# ───────────────────────────────────────────────────────── helper decorator

def admin_required(func):
    """Decorator that combines @login_required and is_admin check."""

    @wraps(func)
    @login_required
    def _wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)

    return _wrapped

# ───────────────────────────────────────────────────────── view: see all orders

@admin_bp.route("/orders")
@admin_required
def view_all_orders():
    # Import inside to avoid circular reference
    from app import db, ROLLS_DATA, Order, OrderItem, User  # noqa: E402

    orders = (
        Order.query.order_by(Order.delivered, Order.placed_at.desc()).all()
    )

    data = []
    for o in orders:
        user = User.query.get(o.user_id)
        items = OrderItem.query.filter_by(order_id=o.id).all()
        rows = [
            {
                "name": ROLLS_DATA[i.roll_id]["name"],
                "size": i.size,
                "qty": i.qty,
            }
            for i in items
        ]
        data.append({"order": o, "user": user, "rows": rows})

    return render_template("admin_orders.html", orders=data)


# ───────────────────────────────────────────────────────── view: mark delivered

@admin_bp.route("/order-delivered/<int:order_id>", methods=["POST"])
@admin_required
def mark_delivered(order_id):
    from app import db, Order  # noqa: E402

    order = Order.query.get_or_404(order_id)
    order.delivered = True
    db.session.commit()
    flash(f"Order #{order.id} marked as delivered!", "success")
    return redirect(url_for("admin.view_all_orders"))
