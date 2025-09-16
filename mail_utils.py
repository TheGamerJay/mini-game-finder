import smtplib
import ssl
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app, render_template, url_for
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


def _use_resend():
    """Check if Resend should be used based on provider config and API key"""
    backend = current_app.config.get("MAIL_BACKEND", "smtp")
    return backend == "resend" and bool(current_app.config.get("RESEND_API_KEY"))


def _serializer():
    """Get the URL safe timed serializer for token generation"""
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_reset_token(email: str) -> str:
    """Generate a time-limited reset token for the given email"""
    return _serializer().dumps(email, salt="password-reset-salt")


def verify_reset_token(token: str, max_age: int) -> str | None:
    """Verify and extract email from reset token. Returns None if invalid/expired."""
    try:
        return _serializer().loads(token, salt="password-reset-salt", max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None


def absolute_url_for(endpoint: str, **values) -> str:
    """Generate absolute URLs with proper scheme for external links"""
    return url_for(
        endpoint,
        _external=True,
        _scheme=current_app.config.get("PREFERRED_URL_SCHEME", "https"),
        **values
    )


def send_email_smtp(to_email: str, subject: str, html_body: str, text_body: str):
    """Send email via SMTP (Gmail, etc.) - matching working SoulBridge AI implementation"""
    smtp_host = current_app.config.get("SMTP_HOST", "").strip()
    smtp_port = current_app.config.get("SMTP_PORT", 587)
    smtp_user = current_app.config.get("SMTP_USER", "").strip()
    smtp_pass = current_app.config.get("SMTP_PASS", "")
    smtp_from = current_app.config.get("SMTP_FROM", "").strip()
    smtp_use_tls = current_app.config.get("SMTP_USE_TLS", True)
    smtp_use_ssl = current_app.config.get("SMTP_USE_SSL", False)

    # Force Gmail SMTP if host looks wrong
    if not smtp_host or "=" in smtp_host:
        smtp_host = "smtp.gmail.com"
        print(f"WARNING: Fixed malformed SMTP_HOST, using: {smtp_host}")

    print(f"DEBUG SMTP: host={smtp_host}, port={smtp_port}, user={smtp_user}, from={smtp_from}, tls={smtp_use_tls}, ssl={smtp_use_ssl}")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Use the same connection method as your working project
    if smtp_use_ssl:
        # SSL connection (port 465)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=15) as server:
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        # TLS connection (port 587) - default
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)


def send_email_resend(to_email: str, subject: str, html_body: str, text_body: str):
    """Send email via Resend API"""
    api_key = current_app.config["RESEND_API_KEY"]
    sender = current_app.config["RESEND_FROM"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body
    }

    response = requests.post("https://api.resend.com/emails", headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def send_email(to_email: str, subject: str, html_body: str, text_body: str):
    """Send email using SMTP (matching SoulBridge AI implementation)"""
    smtp_host = current_app.config.get("SMTP_HOST")
    smtp_from = current_app.config.get("SMTP_FROM")

    # Fallback if SMTP not configured (like SoulBridge AI)
    if not smtp_host or not smtp_from:
        print("SMTP not configured - showing temporary password on page")
        return False

    try:
        send_email_smtp(to_email, subject, html_body, text_body)
        print(f"✅ Email sent successfully via SMTP to: {to_email}")
        return True
    except Exception as e:
        print(f"❌ SMTP email sending error: {e}")
        return False


def send_temporary_password_email(to_email: str, temp_password: str):
    """Send temporary password email"""
    app_name = current_app.config.get("APP_NAME", "Mini Word Finder")

    html_body = f"""
    <h2>Your Temporary Password</h2>
    <p>A password reset was requested for your {app_name} account.</p>
    <p>Your temporary password is: <strong>{temp_password}</strong></p>
    <p>Please log in with this temporary password and change it immediately after logging in.</p>
    <p>If you did not request this reset, please contact support.</p>
    """

    text_body = f"""
    Your Temporary Password

    A password reset was requested for your {app_name} account.

    Your temporary password is: {temp_password}

    Please log in with this temporary password and change it immediately after logging in.

    If you did not request this reset, please contact support.
    """

    subject = f"Your {app_name} temporary password"
    return send_email(to_email, subject, html_body, text_body)


def send_password_reset_email(to_email: str, token: str):
    """Send password reset email with token"""
    reset_url = absolute_url_for("core.reset_token", token=token)
    expires = int(current_app.config.get("PASSWORD_RESET_TOKEN_MAX_AGE", 3600) / 60)

    html = render_template(
        "email/reset_password.html",
        reset_url=reset_url,
        expires_in_minutes=expires
    )

    text = render_template(
        "email/reset_password.txt",
        reset_url=reset_url,
        expires_in_minutes=expires
    )

    subject = "Reset your Mini Word Finder password"
    send_email(to_email, subject, html, text)