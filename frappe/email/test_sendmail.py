import inspect
from unittest.mock import patch

import frappe


def test_sendmail_accepts_redaction_flag() -> None:
    """User welcome emails may request post-send message redaction."""

    assert "redact_message_after_send" in inspect.signature(frappe.sendmail).parameters

    with patch("frappe.email.doctype.email_queue.email_queue.QueueBuilder") as queue_builder:
        queue_builder.return_value.process.return_value = None

        frappe.sendmail(
            recipients=["test@example.invalid"],
            subject="Test",
            message="Test",
            redact_message_after_send=True,
        )

    assert queue_builder.call_args.kwargs["redact_message_after_send"] is True
