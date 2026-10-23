from __future__ import annotations

import smtplib
from email.message import EmailMessage


class SmtpMailer:
    def __init__(self, host: str, port: int, sender: str) -> None:
        self._host = host
        self._port = port
        self._sender = sender

    def send(self, recipient: str, subject: str, text: str) -> None:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(text)
        with smtplib.SMTP(self._host, self._port, timeout=10) as client:
            client.send_message(message)
