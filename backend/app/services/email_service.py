"""
Email service for OMNI-RANK campaigns.
Handles sending transactional and marketing emails.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional
from app.email_templates import (
    research_report_email,
    nurture_email_1,
    nurture_email_2,
    nurture_email_3,
)

# Email service configuration
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "sendgrid")  # or "mailgun", "smtp"
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


class EmailService:
    """Base email service."""

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        from_email: str = "reports@omni-rank.com",
    ) -> bool:
        """Send an email. Override in subclasses."""
        raise NotImplementedError

    def send_research_report(self, to_email: str, unsubscribe_link: str) -> bool:
        """Send monthly research report."""
        next_month = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1)
        month_year = next_month.strftime("%B %Y")
        subject, html = research_report_email(
            month_year,
            {},  # report_data
            to_email,
            unsubscribe_link,
        )
        return self.send_email(to_email, subject, html)

    def send_nurture_sequence(
        self, to_email: str, sequence_number: int, vertical: str, unsubscribe_link: str
    ) -> bool:
        """Send nurture email based on sequence."""
        if sequence_number == 1:
            subject, html = nurture_email_1(to_email, unsubscribe_link)
        elif sequence_number == 2:
            subject, html = nurture_email_2(to_email, vertical, unsubscribe_link)
        elif sequence_number == 3:
            subject, html = nurture_email_3(to_email, unsubscribe_link)
        else:
            return False

        return self.send_email(to_email, subject, html)


class SendGridService(EmailService):
    """SendGrid email service."""

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        from_email: str = "reports@omni-rank.com",
    ) -> bool:
        """Send email via SendGrid."""
        if not SENDGRID_API_KEY:
            print("Warning: SENDGRID_API_KEY not configured")
            return False

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail

            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=text_body or subject,
                html_content=html_body,
            )

            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)
            return response.status_code in [200, 201, 202]
        except Exception as e:
            print(f"SendGrid error: {e}")
            return False


class MockEmailService(EmailService):
    """Mock email service for development."""

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        from_email: str = "reports@omni-rank.com",
    ) -> bool:
        """Mock send (log to console)."""
        print(f"\n[MOCK EMAIL]")
        print(f"To: {to_email}")
        print(f"From: {from_email}")
        print(f"Subject: {subject}")
        print(f"Body: {html_body[:100]}...")
        return True


def get_email_service() -> EmailService:
    """Get configured email service."""
    if EMAIL_PROVIDER == "sendgrid" and SENDGRID_API_KEY:
        return SendGridService()
    else:
        # Default to mock for development
        return MockEmailService()


# Subscription management
class SubscriptionManager:
    """Handle email subscription state and nurture sequence.

    Takes the app's Supabase REST helper (main._supabase_rest) instead of the
    supabase-py client, which is not a project dependency.
    """

    def __init__(self, db_fn):
        # db_fn(method, path, payload=None, params="") -> dict | list
        self.db = db_fn

    def subscribe(
        self, email: str, vertical: str, source: str = "research_report"
    ) -> bool:
        """Add subscriber and initialize nurture sequence."""
        try:
            existing = self.db("get", "email_subscribers", params=f"email=eq.{email}")
            if existing:
                # Re-subscribe: clear any previous unsubscribe
                self.db("patch", f"email_subscribers?email=eq.{email}", {
                    "unsubscribed_at": None,
                    "vertical": vertical,
                })
                return True
            self.db("post", "email_subscribers", {
                "email": email,
                "vertical": vertical,
                "source": source,
                "subscribed_at": datetime.utcnow().isoformat(),
                "unsubscribed_at": None,
                "nurture_sequence": 0,
                "last_email_sent": None,
                "email_count": 0,
            })
            return True
        except Exception as e:
            print(f"Subscription error: {e}")
            return False

    def unsubscribe(self, email: str) -> bool:
        """Unsubscribe email address."""
        try:
            self.db("patch", f"email_subscribers?email=eq.{email}", {
                "unsubscribed_at": datetime.utcnow().isoformat(),
            })
            return True
        except Exception as e:
            print(f"Unsubscribe error: {e}")
            return False

    def get_active_subscribers(self, limit: int = 100) -> list:
        """Get subscribers ready for nurture emails."""
        try:
            return self.db(
                "get", "email_subscribers",
                params=f"unsubscribed_at=is.null&limit={limit}",
            ) or []
        except Exception as e:
            print(f"Query error: {e}")
            return []

    def update_subscription_state(
        self, email: str, sequence: int, last_sent: str
    ) -> bool:
        """Update subscriber after sending nurture email."""
        try:
            self.db("patch", f"email_subscribers?email=eq.{email}", {
                "nurture_sequence": sequence,
                "last_email_sent": last_sent,
            })
            return True
        except Exception as e:
            print(f"Update error: {e}")
            return False
