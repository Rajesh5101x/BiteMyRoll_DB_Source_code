# admin.py  (run with:  python admin.py)
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():               # ⬅️  provides the context
    admin = User(
        username = "admin",
        email    = "admin@example.com",
        pw_hash  = generate_password_hash("adminpass"),
        is_admin = True
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin user created!")
