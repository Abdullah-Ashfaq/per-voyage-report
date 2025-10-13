import os
import smtplib
import ssl
from email.utils import formatdate, make_msgid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


# ----------------------------------------------------------
#  Helper: HTML → Plain Text fallback
# ----------------------------------------------------------
def _plaintext_fallback(html: str) -> str:
    """
    Very simple HTML→text fallback.
    For a better result you can use html2text, but we avoid extra deps here.
    """
    import re
    text = html
    # replace <br> / <p> with newlines
    text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", text)
    text = re.sub(r"(?i)</\s*p\s*>", "\n\n", text)
    # strip tags
    text = re.sub(r"<[^>]+>", "", text)
    # unescape entities
    from html import unescape
    text = unescape(text)
    # collapse whitespace
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()
    return text


# ----------------------------------------------------------
#  Core: Send HTML Email with optional attachment
# ----------------------------------------------------------
def send_html_report(
    subject: str,
    html_body: str,
    from_addr: str | None = None,
    to_addrs: list[str] | None = None,
    attach_html_path: str | None = None,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_pass: str | None = None,
    use_starttls: bool = True,
):
    """
    Send an HTML report via SMTP with a plain-text fallback and optional attachment.

    Defaults are read from environment variables if not provided:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO (comma-separated)

    Example SMTP settings:
      - Office 365: smtp.office365.com:587 (STARTTLS)
      - Gmail: smtp.gmail.com:587 (STARTTLS; App Password required)
    """
    # Pull defaults from env if needed
    smtp_host = smtp_host or os.getenv("SMTP_HOST")
    smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
    smtp_user = smtp_user or os.getenv("SMTP_USER")
    smtp_pass = smtp_pass or os.getenv("SMTP_PASS")

    if not from_addr:
        from_addr = os.getenv("EMAIL_FROM", "")
    if not to_addrs:
        env_to = os.getenv("EMAIL_TO", "")
        to_addrs = [x.strip() for x in env_to.split(",") if x.strip()]

    if not (smtp_host and smtp_port and smtp_user and smtp_pass and from_addr and to_addrs):
        missing = []
        for k, v in {
            "SMTP_HOST": smtp_host,
            "SMTP_PORT": smtp_port,
            "SMTP_USER": smtp_user,
            "SMTP_PASS": smtp_pass,
            "EMAIL_FROM": from_addr,
            "EMAIL_TO": ",".join(to_addrs) if to_addrs else "",
        }.items():
            if not v:
                missing.append(k)
        raise RuntimeError(f"Missing SMTP configuration: {', '.join(missing)}")

    # Build message
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()

    # Alternative part (text + html)
    alt = MIMEMultipart("alternative")
    text = _plaintext_fallback(html_body)
    alt.attach(MIMEText(text, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    # Optional attachment
    if attach_html_path:
        with open(attach_html_path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="html")
        part.add_header("Content-Disposition", "attachment", filename=os.path.basename(attach_html_path))
        msg.attach(part)

    # Send email
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if use_starttls:
            server.starttls(context=context)
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, to_addrs, msg.as_string())

    print(f"✅ Email sent successfully to {', '.join(to_addrs)}")


# ----------------------------------------------------------
#  Convenience Wrapper for Voyage Reports
# ----------------------------------------------------------
def send_voyage_report_email(report_path: str, subject_prefix: str = "[Voyage Report]"):
    """
    Convenience helper to send a voyage HTML report.
    Uses environment variables for all SMTP and recipient settings.

    Env vars required:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO
    """
    from datetime import datetime
    import os

    # Derive voyage name from file
    filename = os.path.basename(report_path)
    if "to" in filename.lower():
        voyage_label = (
            filename.replace("voyage_", "")
            .replace(".html", "")
            .replace("_", " ")
            .title()
        )
    else:
        voyage_label = datetime.utcnow().strftime("%Y-%m-%d")

    subject = f"{subject_prefix} {voyage_label}"

    # Load HTML content
    with open(report_path, "r", encoding="utf-8") as f:
        html_body = f.read()

    # Send the report
    send_html_report(
        subject=subject,
        html_body=html_body,
        from_addr=None,     # pulled from env
        to_addrs=None,      # pulled from env
        attach_html_path=report_path,
    )

    print(f"📧 Voyage report emailed successfully → {voyage_label}")
