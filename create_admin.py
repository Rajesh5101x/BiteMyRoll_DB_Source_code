# create_admin.py
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    existing_admin = User.query.filter_by(username="admin").first()

    if existing_admin:
        print("Admin user already exists!")
    else:
        admin = User(
            username="admin2",
            email="admin2@example.com",
            pw_hash=generate_password_hash("adminpass"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created!")
