from flask import render_template, request, redirect, url_for, session
from itsdangerous import URLSafeTimedSerializer
from models import db, User
from functools import wraps

# These will be provided when the routes are registered
SECRET_KEY = None
APP_NAME = None

def register_routes(app, secret_key=None, app_name=None):
    global SECRET_KEY, APP_NAME
    SECRET_KEY = secret_key
    APP_NAME = app_name
    # Auth decorators
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated_function
    
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("is_admin"):
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return decorated_function

    # Routes: Auth
    @app.get("/login")
    def login_form():
        return render_template("login.html")
    
    @app.post("/login")
    def login():
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return render_template("login.html", flash_msg=("error", "Invalid email or password"))
        
        session["user_id"] = user.id
        session["is_admin"] = bool(user.is_admin)
        return redirect(url_for("home"))
    
    @app.get("/register")
    def register_form():
        return render_template("register.html")
    
    @app.post("/register")
    def register():
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip() or username
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        # Basic validation
        if not username or len(username) < 3:
            return render_template("register.html", flash_msg=("error", "Username must be at least 3 characters"))
        
        if not email or "@" not in email:
            return render_template("register.html", flash_msg=("error", "Valid email address required"))
            
        if not password or len(password) < 6:
            return render_template("register.html", flash_msg=("error", "Password must be at least 6 characters"))
        
        # Check if username exists and suggest alternatives
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"DEBUG: Username '{username}' already exists - User ID: {existing_user.id}")
            # Suggest alternative usernames
            suggestions = []
            for i in range(2, 6):
                alt_username = f"{username}{i}"
                if not User.query.filter_by(username=alt_username).first():
                    suggestions.append(alt_username)
            
            suggestion_text = f" Try: {', '.join(suggestions[:3])}" if suggestions else ""
            return render_template("register.html", flash_msg=("error", f"Username '{username}' already taken.{suggestion_text}"))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            print(f"DEBUG: Email '{email}' already exists - User ID: {existing_email.id}")
            return render_template("register.html", flash_msg=("error", "Email already registered"))
            
        print(f"DEBUG: No conflicts found for username '{username}' and email '{email}'. Proceeding with registration...")
        
        try:
            print(f"DEBUG: Creating user object for username='{username}', email='{email}'")
            user = User(
                username=username, 
                display_name=display_name, 
                email=email,
                mini_word_credits=10  # Starting credits
            )
            print(f"DEBUG: User object created successfully")
            
            user.set_password(password)
            print(f"DEBUG: Password set successfully")
            
            db.session.add(user)
            print(f"DEBUG: User added to session, attempting commit...")
            
            db.session.commit()
            print(f"DEBUG: User committed successfully! User ID: {user.id}")
            
            session["user_id"] = user.id
            session["is_admin"] = bool(user.is_admin)
            print(f"DEBUG: Session set, redirecting to home")
            return redirect(url_for("home"))
            
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Registration error occurred: {type(e).__name__}: {str(e)}")
            
            # Check if it's a uniqueness constraint error
            if "unique constraint" in str(e).lower() or "already exists" in str(e).lower():
                return render_template("register.html", flash_msg=("error", f"Username or email already taken. Please try different values."))
            else:
                return render_template("register.html", flash_msg=("error", f"Registration failed: {str(e)}"))
    
    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))
    
    @app.get("/reset")
    def reset_request():
        return render_template("reset_token.html")
    
    @app.post("/reset")
    def reset_token():
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return render_template("reset_token.html", flash_msg=("error", "Email not found"))
        
        s = URLSafeTimedSerializer(SECRET_KEY)
        token = s.dumps(email, salt="reset-password")
        # TODO: Send email with reset link
        return render_template("reset_token.html", flash_msg=("ok", "Check your email for reset instructions"))

    # Return nothing - routes are registered directly on the app
    return None
