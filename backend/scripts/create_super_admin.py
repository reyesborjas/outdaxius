# scripts/create_super_admin.py
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
# Was `from app.utils.security import hash_password`, which is unimportable: app/utils.py
# shadows the app/utils/ directory (which has no __init__.py), so this script raised
# ModuleNotFoundError before it ever prompted. app.core.security is the module the login
# endpoint verifies against, which is what a bootstrapped admin needs to match anyway.
from app.core.security import get_password_hash as hash_password
from datetime import datetime
from contextlib import contextmanager

@contextmanager
def session_scope():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
        
def main():
    email = input("Admin email: ")
    password = input("Admin password: ")
    full_name = input("Admin full name: ")

    first_name, last_name = (full_name.split(" ", 1) + [""])[:2]

    with session_scope() as db:   # ✅ no Pylance warning
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print("User already exists. Updating password...")
            existing.password_hash = hash_password(password)
            db.commit()
            print("Password updated.")
        else:
            user = User(
                email=email,
                password_hash=hash_password(password),
                display_name="Admin",
                first_name=first_name,
                last_name=last_name,
                role="admin",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print("Super admin created:", user.email)

if __name__ == "__main__":
    main()
