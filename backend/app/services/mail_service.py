"""Email sending service using smtplib SMTP_SSL."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, roll: str, otp: str) -> None:
    """
    Send an OTP email via Gmail SMTP_SSL.
    Raises RuntimeError on failure.
    """
    gmail_user = current_app.config["GMAIL_USER"]
    gmail_password = current_app.config["GMAIL_APP_PASSWORD"]
    expiry = current_app.config["OTP_EXPIRY_MINUTES"]

    if not gmail_user or not gmail_password:
        raise RuntimeError(
            "GMAIL_USER and GMAIL_APP_PASSWORD must be set to send emails."
        )

    subject = f"Your Face Registration OTP — {otp}"
    html_body = _build_html(roll, otp, expiry)
    plain_body = _build_plain(roll, otp, expiry)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())
        logger.info("OTP email sent to %s", to_email)
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for %s", gmail_user)
        raise RuntimeError(
            "Email authentication failed. Check your GMAIL_APP_PASSWORD in .env."
        )
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", to_email, exc)
        raise RuntimeError("Could not send the OTP email. Please try again later.")


def _build_plain(roll: str, otp: str, expiry: int) -> str:
    return (
        f"Your one-time password (OTP) for face registration is:\n\n"
        f"  {otp}\n\n"
        f"This OTP is valid for {expiry} minutes.\n"
        f"Do not share it with anyone.\n\n"
        f"If you did not request this, please ignore this email."
    )


def _build_html(roll: str, otp: str, expiry: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;color:#1a1a1a;padding:32px;max-width:480px;margin:auto">
  <h2 style="color:#2563eb;margin-bottom:4px">Face Registration</h2>
  <p style="color:#6b7280;margin-top:0">IIITK Student Portal</p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">
  <p>Hello <strong>{roll}</strong>,</p>
  <p>Your one-time password (OTP) for face photo registration is:</p>
  <div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#1d4ed8;
              background:#eff6ff;border-radius:8px;padding:16px;text-align:center;
              margin:24px 0">
    {otp}
  </div>
  <p style="color:#6b7280;font-size:14px">
    This OTP expires in <strong>{expiry} minutes</strong>. Do not share it with anyone.
  </p>
  <p style="color:#6b7280;font-size:12px">
    If you did not request this OTP, please ignore this email.
  </p>
</body>
</html>"""

