"""Email sending — STUB implementation (explicitly allowed by Prompt 0).

The real email-sending integration (e.g. SendGrid / SES / Mailgun) is
deferred. For now, every "send_email" call prints a clearly-marked line
to stdout that includes the recipient + body, so dev / test runs can grep
the reset link out of the server logs.

When you wire in the real provider, replace the body of send_email() with
the provider SDK call. The function signature (to_email, subject, body)
should stay stable so callers don't change.

Prompt 0 rule: "EXCEPT where a phase explicitly tells you to stub something
(e.g. 'stub the email send with a console.log')". Phase 2 tells us to stub
the email send. This is the stub.

Test hook: if the env var EMAIL_STUB_FILE is set, the full email body is
also appended to that file path. This lets automated tests extract the
reset token reliably without parsing subprocess stdout. The hook is inert
in production (env var is not set).
"""

from __future__ import annotations

import os
import sys


def send_email(to_email: str, subject: str, body: str) -> None:
    """Stub: print the email to stdout instead of sending it.

    The output is prefixed with [EMAIL-STUB] so it is greppable from server
    logs. The body is printed verbatim — for the password reset flow, the
    body contains the reset link, which the test harness extracts.

    If EMAIL_STUB_FILE is set in the environment, the email is also appended
    to that file (test hook — not used in production).
    """
    output = (
        f"\n[EMAIL-STUB] ----\n"
        f"To: {to_email}\n"
        f"Subject: {subject}\n"
        f"Body:\n{body}\n"
        f"[EMAIL-STUB] ----\n"
    )
    print(output, file=sys.stdout, flush=True)

    # Test hook: write to a file so tests can read the reset token without
    # parsing subprocess stdout (which has buffering issues across processes).
    stub_file = os.environ.get("EMAIL_STUB_FILE")
    if stub_file:
        try:
            with open(stub_file, "a", encoding="utf-8") as f:
                f.write(output)
        except OSError:
            # Don't let a broken test hook crash the auth flow.
            pass


def build_password_reset_email(
    to_email: str, full_name: str, reset_token: str
) -> tuple[str, str]:
    """Build the (subject, body) tuple for a password-reset email.

    Returns the subject and body. The reset link points at the FRONTEND_URL
    password-reset page, which will read the token from the URL fragment and
    POST it to /api/v1/auth/password-reset/confirm.
    """
    subject = "Reset your OfferForge password"
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    body = (
        f"Hi {full_name},\n\n"
        f"We received a request to reset your password. Click the link below "
        f"to choose a new one. The link expires in "
        f"{settings.PASSWORD_RESET_TTL_MINUTES} minutes.\n\n"
        f"    {reset_url}\n\n"
        f"If you didn't request a password reset, you can safely ignore this "
        f"email — your password has not been changed.\n\n"
        f"— OfferForge"
    )
    return subject, body


# Local import to avoid a circular import at module load (settings is fine,
# but kept here so the stub module has zero hard deps and can be swapped out
# without touching the rest of the codebase).
from app.core.config import settings  # noqa: E402
