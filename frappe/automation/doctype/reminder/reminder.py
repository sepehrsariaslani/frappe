# Copyright (c) 2023, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.data import add_to_date, get_datetime, now_datetime


class Reminder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText
		notified: DF.Check
		remind_at: DF.Datetime
		reminder_docname: DF.DynamicLink | None
		reminder_doctype: DF.Link | None
		user: DF.Link
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=30):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Reminder")
		frappe.db.delete(table, filters=(table.remind_at < (Now() - Interval(days=days))))

	def validate(self):
		self.user = frappe.session.user
		if get_datetime(self.remind_at) < now_datetime():
			frappe.throw(_("Reminder cannot be created in past."))

	def send_reminder(self):
		if self.notified:
			return

		sent = False

		try:
			notification = frappe.new_doc("Notification Log")
			notification.for_user = self.user
			notification.set("type", "Alert")
			notification.document_type = self.reminder_doctype
			notification.document_name = self.reminder_docname
			notification.subject = self.description
			notification.insert()
			sent = True
		except Exception:
			self.log_error("Failed to send reminder")

		# HRMS mobile app reads from PWA Notification doctype.
		# Create a matching entry so reminder alerts are visible in-app and can trigger push notifications.
		if frappe.db.exists("DocType", "PWA Notification"):
			try:
				pwa_notification = frappe.new_doc("PWA Notification")
				pwa_notification.to_user = self.user
				pwa_notification.from_user = self.user
				pwa_notification.message = self.description
				pwa_notification.reference_document_type = self.reminder_doctype or "Reminder"
				pwa_notification.reference_document_name = self.reminder_docname or self.name
				pwa_notification.insert(ignore_permissions=True)
				sent = True
			except Exception:
				self.log_error("Failed to send reminder as PWA notification")

		if sent:
			self.db_set("notified", 1, update_modified=False)


@frappe.whitelist()
def create_new_reminder(
	remind_at: str,
	description: str,
	reminder_doctype: str | None = None,
	reminder_docname: str | None = None,
):
	reminder = frappe.new_doc("Reminder")

	reminder.description = description
	reminder.remind_at = remind_at
	reminder.reminder_doctype = reminder_doctype
	reminder.reminder_docname = reminder_docname

	return reminder.insert()


def send_reminders():
	# Ensure that we send all reminders that might be before next job execution.
	job_freq = 15 * 60  # 15 minutes, as specified in hooks.py
	upper_threshold = add_to_date(now_datetime(), seconds=job_freq, as_string=True, as_datetime=True)
	backlog_minutes = cint(frappe.conf.get("reminder_backlog_minutes", 60 * 24 * 30))
	lower_threshold = add_to_date(
		now_datetime(),
		minutes=-max(backlog_minutes, 60),
		as_string=True,
		as_datetime=True,
	)
	batch_size = max(cint(frappe.conf.get("reminder_batch_size", 500)), 1)

	pending_reminders = frappe.get_all(
		"Reminder",
		filters=[
			("remind_at", "<=", upper_threshold),
			("remind_at", ">=", lower_threshold),
			("notified", "=", 0),
		],
		order_by="remind_at asc",
		limit_page_length=batch_size,
		pluck="name",
		ignore_ifnull=True,
	)

	for reminder in pending_reminders:
		frappe.get_doc("Reminder", reminder).send_reminder()
