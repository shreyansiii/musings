import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from django.core.mail.backends.base import BaseEmailBackend

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


class GmailAPIBackend(BaseEmailBackend):
    """
    Django email backend that sends mail through the Gmail API
    (HTTPS) instead of SMTP. Works on hosts that block SMTP ports.
    """

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        service = self._get_service()
        sent_count = 0

        for message in email_messages:
            try:
                raw = self._build_raw_message(message)
                service.users().messages().send(
                    userId="me", body={"raw": raw}
                ).execute()
                sent_count += 1
            except Exception as e:
                if not self.fail_silently:
                    raise
                print(f"Gmail API send failed: {e}")

        return sent_count

    def _get_service(self):
        creds = Credentials(
            token=None,
            refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["GMAIL_CLIENT_ID"],
            client_secret=os.environ["GMAIL_CLIENT_SECRET"],
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )
        creds.refresh(Request())
        return build("gmail", "v1", credentials=creds)

    def _build_raw_message(self, message):
        mime_msg = MIMEMultipart("alternative")
        mime_msg["To"] = ", ".join(message.to)
        mime_msg["From"] = os.environ.get(
            "GMAIL_SENDER_EMAIL", message.from_email
        )
        mime_msg["Subject"] = message.subject

        # Plain text body
        mime_msg.attach(MIMEText(message.body, "plain"))

        # If it's an HTML email (EmailMultiAlternatives), attach the HTML part too
        if hasattr(message, "alternatives"):
            for content, mimetype in message.alternatives:
                if mimetype == "text/html":
                    mime_msg.attach(MIMEText(content, "html"))

        raw_bytes = mime_msg.as_bytes()
        raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode()
        return raw_b64