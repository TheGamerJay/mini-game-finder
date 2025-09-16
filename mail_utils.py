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
    """Send email via SMTP (Gmail, etc.)"""
    smtp_server = current_app.config.get("MAIL_SERVER") or current_app.config.get("SMTP_HOST")
    port = current_app.config.get("MAIL_PORT", 587)
    username = current_app.config.get("MAIL_USERNAME") or current_app.config.get("SMTP_USER")
    password = current_app.config.get("MAIL_PASSWORD") or current_app.config.get("SMTP_PASS")
    sender = current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("SMTP_FROM")
    use_tls = current_app.config.get("MAIL_USE_TLS", True)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        if use_tls:
            server.starttls(context=context)
        if username and password:
            server.login(username, password)
        server.sendmail(sender, [to_email], msg.as_string())


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
    """Send email using the configured method (Resend API or SMTP)"""
    # Use provider selection based on MAIL_BACKEND config
    if _use_resend():
        try:
            send_email_resend(to_email, subject, html_body, text_body)
            print(f"Email sent via Resend API to {to_email}")
            return
        except Exception as e:
            print(f"Resend API failed: {e}")
            # Fall back to SMTP if Resend fails and SMTP is configured
            if current_app.config.get("MAIL_SERVER") and current_app.config.get("MAIL_USERNAME"):
                print("Falling back to SMTP...")
            else:
                raise

    # Use SMTP (primary method when provider=smtp or fallback)
    smtp_server = current_app.config.get("MAIL_SERVER") or current_app.config.get("SMTP_HOST")
    smtp_username = current_app.config.get("MAIL_USERNAME") or current_app.config.get("SMTP_USER")

    if smtp_server and smtp_username:
        try:
            send_email_smtp(to_email, subject, html_body, text_body)
            print(f"Email sent via SMTP to {to_email}")
        except Exception as e:
            print(f"SMTP failed: {e}")
            raise
    else:
        print(f"No email configuration available. Would send email to {to_email}: {subject}")
        # In development, just print the email details


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