from app import create_app
from models import db

def init_database():
    app = create_app()
    with app.app_context():
        # This will drop all tables
        db.drop_all()
        # This will create all tables
        db.create_all()
        print("Database initialized!")

if __name__ == "__main__":
    init_database()
