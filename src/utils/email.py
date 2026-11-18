"""Email sending utilities via SMTP."""
from __future__ import annotations

import ssl
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


class EmailHandlerError(Exception):
    """Raised when sending email fails."""


class EmailHandler:
    """Full-featured email handler with multipart structure and attachments."""

    def __init__(
        self,
        smtp_server: str,
        port: int,
        sender_email: str,
        password: str,
        login_user: str | None = None,
        use_tls: bool = True,
    ):
        self.smtp_server = smtp_server
        self.port = port
        self.sender_email = sender_email
        self.password = password
        self.login_user = login_user or sender_email
        self.use_tls = use_tls

    def send_email(
        self,
        receiver_email: str | list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list[str] | None = None,
        reply_to: str | None = None,
    ) -> None:
        """Send email with plain text + optional HTML + attachments."""
        subject = subject.strip().replace("\n", " ").replace("\r", "")
        body = body.strip()
        html_body = html_body.strip() if html_body else None

        to_addrs = [receiver_email] if isinstance(receiver_email, str) else list(receiver_email)
        cc = cc or []
        bcc = bcc or []
        all_recipients = to_addrs + cc + bcc

        msg = MIMEMultipart("mixed")
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(to_addrs)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(body, "plain"))
        if html_body:
            alt.attach(MIMEText(html_body, "html"))
        msg.attach(alt)

        if attachments:
            for file_path in attachments:
                path = Path(file_path)
                if not path.is_file():
                    continue
                with open(path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={path.name}",
                    )
                    msg.attach(part)

        context = ssl.create_default_context()
        try:
            if self.use_tls:
                with smtplib.SMTP(self.smtp_server, self.port) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.login_user, self.password)
                    server.send_message(msg, from_addr=self.sender_email, to_addrs=all_recipients)
            else:
                with smtplib.SMTP_SSL(self.smtp_server, self.port, context=context) as server:
                    server.login(self.login_user, self.password)
                    server.send_message(msg, from_addr=self.sender_email, to_addrs=all_recipients)
        except Exception as e:
            raise EmailHandlerError(f"Failed to send email: {e}") from e