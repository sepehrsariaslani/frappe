# Copyright (c) 2026, Frappe Technologies and Contributors
# License: MIT. See LICENSE

from __future__ import annotations

import hashlib
import json
import secrets
import time
from typing import Any

import requests

import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.core.doctype.sms_settings.sms_settings import get_headers
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

OTP_LENGTH = 6
OTP_EXPIRY_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
CHALLENGE_CACHE_KEY = "mobile_login:challenge:{challenge_id}"
COOLDOWN_CACHE_KEY = "mobile_login:cooldown:{mobile}"
ACTIVE_CHALLENGE_CACHE_KEY = "mobile_login:active_challenge:{mobile}"


def _normalize_mobile(raw_mobile: str | None) -> str | None:
	if not raw_mobile:
		return None

	translation_table = str.maketrans(
		{
			"۰": "0",
			"۱": "1",
			"۲": "2",
			"۳": "3",
			"۴": "4",
			"۵": "5",
			"۶": "6",
			"۷": "7",
			"۸": "8",
			"۹": "9",
		}
	)
	raw_mobile = raw_mobile.translate(translation_table)

	digits = "".join(ch for ch in raw_mobile if ch.isdigit())
	if digits.startswith("0098") and len(digits) >= 14:
		digits = "0" + digits[4:]
	elif digits.startswith("98") and len(digits) >= 12:
		digits = "0" + digits[2:]
	elif digits.startswith("9") and len(digits) == 10:
		digits = "0" + digits

	if len(digits) != 11 or not digits.startswith("09"):
		return None

	return digits


def _hash_otp(mobile: str, otp: str) -> str:
	secret = frappe.local.conf.get("encryption_key") or frappe.local.conf.get("db_password") or "mobile-login"
	return hashlib.sha256(f"{mobile}:{otp}:{secret}".encode()).hexdigest()


def _challenge_key(challenge_id: str) -> str:
	return CHALLENGE_CACHE_KEY.format(challenge_id=challenge_id)


def _cooldown_key(normalized_mobile: str) -> str:
	return COOLDOWN_CACHE_KEY.format(mobile=normalized_mobile)


def _active_challenge_key(normalized_mobile: str) -> str:
	return ACTIVE_CHALLENGE_CACHE_KEY.format(mobile=normalized_mobile)


def _get_active_challenge_id(normalized_mobile: str) -> str | None:
	challenge_id = frappe.cache.get_value(_active_challenge_key(normalized_mobile))
	if isinstance(challenge_id, bytes):
		challenge_id = challenge_id.decode()
	return challenge_id if isinstance(challenge_id, str) and challenge_id else None


def _save_active_challenge_id(normalized_mobile: str, challenge_id: str):
	frappe.cache.set_value(
		_active_challenge_key(normalized_mobile), challenge_id, expires_in_sec=OTP_EXPIRY_SECONDS
	)


def _clear_active_challenge_id(normalized_mobile: str, challenge_id: str | None = None):
	if challenge_id:
		active_challenge = _get_active_challenge_id(normalized_mobile)
		if active_challenge and active_challenge != challenge_id:
			return
	frappe.cache.delete_value(_active_challenge_key(normalized_mobile))


def _remaining_cooldown_seconds(normalized_mobile: str) -> int | None:
	cached_value = frappe.cache.get_value(_cooldown_key(normalized_mobile))
	if cached_value is None:
		return None

	cooldown_until = 0
	try:
		cooldown_until = int(cached_value)
	except Exception:
		cooldown_until = 0

	if cooldown_until <= 0:
		return OTP_RESEND_COOLDOWN_SECONDS

	remaining = cooldown_until - int(time.time())
	if remaining <= 0:
		frappe.cache.delete_value(_cooldown_key(normalized_mobile))
		return None

	return remaining


def _load_challenge(challenge_id: str) -> dict[str, Any] | None:
	payload = frappe.cache.get_value(_challenge_key(challenge_id))
	if not payload:
		return None
	if isinstance(payload, bytes):
		payload = payload.decode()
	if isinstance(payload, str):
		return json.loads(payload)
	return payload


def _save_challenge(challenge_id: str, payload: dict[str, Any], expires_in_sec: int = OTP_EXPIRY_SECONDS):
	frappe.cache.set_value(_challenge_key(challenge_id), json.dumps(payload), expires_in_sec=expires_in_sec)


def _delete_challenge(challenge_id: str):
	frappe.cache.delete_value(_challenge_key(challenge_id))


def _find_user_by_mobile(normalized_mobile: str) -> str | None:
	users = frappe.db.sql(
		"""
		select name, mobile_no, phone
		from `tabUser`
		where enabled = 1
			and name != 'Administrator'
			and (ifnull(mobile_no, '') != '' or ifnull(phone, '') != '')
		""",
		as_dict=True,
	)

	for user in users:
		for mobile in (user.mobile_no, user.phone):
			if _normalize_mobile(mobile) == normalized_mobile:
				return user.name

	return None


def _get_verify_template_settings(ss) -> tuple[int | None, str]:
	template_id = None
	parameter_name = "code"

	for row in ss.get("parameters") or []:
		key = (row.parameter or "").strip().lower()
		if row.header or not key:
			continue
		if key in {"templateid", "template_id"}:
			parsed_template_id = cint(row.value)
			template_id = parsed_template_id if parsed_template_id > 0 else None
		elif key in {"parametername", "parameter_name", "otp_parameter_name"} and row.value:
			parameter_name = row.value

	return template_id, parameter_name


def _log_mobile_otp_event(
	event_type: str,
	mobile: str | None = None,
	user: str | None = None,
	challenge_id: str | None = None,
	send_mode: str | None = None,
	provider_status: int | None = None,
	provider_message: str | None = None,
	provider_reference: str | None = None,
	template_id: int | None = None,
	line_number: int | None = None,
	request_payload: dict[str, Any] | None = None,
	response_payload: dict[str, Any] | None = None,
	error: str | None = None,
):
	try:
		if not frappe.db.exists("DocType", "Mobile Login OTP Event"):
			return

		doc = frappe.get_doc(
			{
				"doctype": "Mobile Login OTP Event",
				"event_type": event_type,
				"mobile": mobile,
				"user": user,
				"challenge_id": challenge_id,
				"send_mode": send_mode,
				"provider_status": provider_status,
				"provider_message": provider_message,
				"provider_reference": provider_reference,
				"template_id": template_id,
				"line_number": line_number,
				"request_payload": json.dumps(request_payload or {}, ensure_ascii=False),
				"response_payload": json.dumps(response_payload or {}, ensure_ascii=False),
				"error_details": error,
			}
		)
		doc.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Mobile OTP Event Logging Failed")


def _get_sms_line_number(ss, headers: dict[str, str]) -> int | None:
	for row in ss.get("parameters") or []:
		key = (row.parameter or "").strip().lower()
		if row.header or not key:
			continue
		if key in {"linenumber", "line_number", "line"}:
			return cint(row.value) or None

	# Fallback: fetch first usable line from sms.ir using API key.
	try:
		line_response = requests.get("https://api.sms.ir/v1/line", headers=headers, timeout=15)
		line_response.raise_for_status()
		line_data = line_response.json() if line_response.content else {}
		lines = (line_data or {}).get("data") or []
		if lines:
			for line in lines:
				line_str = str(line)
				if line_str.startswith("5"):
					return cint(line) or None
			return cint(lines[0]) or None
	except Exception:
		return None

	return None


def _send_bulk_sms_with_api_key(
	ss, mobile: str, otp_code: str, headers: dict[str, str], user: str, challenge_id: str
):
	line_number = _get_sms_line_number(ss, headers)
	if not line_number:
		_log_mobile_otp_event(
			event_type="sms_failed",
			mobile=mobile,
			user=user,
			challenge_id=challenge_id,
			send_mode="bulk",
			error="Missing lineNumber",
		)
		frappe.throw(
			_("Missing lineNumber for SMS sending. Add lineNumber in SMS Settings static parameters.")
		)

	bulk_payload = {
		"lineNumber": line_number,
		# Keep OTP text short and localized to avoid multi-part billing on some routes.
		"messageText": f"کد ورود شما: {otp_code}",
		"mobiles": [mobile],
	}
	safe_payload = dict(bulk_payload)
	safe_payload["messageText"] = "OTP_MESSAGE"
	try:
		bulk_response = requests.post(
			"https://api.sms.ir/v1/send/bulk", json=bulk_payload, headers=headers, timeout=15
		)
		bulk_response.raise_for_status()
		bulk_data = bulk_response.json() if bulk_response.content else {}
		if cint((bulk_data or {}).get("status")) != 1:
			_log_mobile_otp_event(
				event_type="sms_failed",
				mobile=mobile,
				user=user,
				challenge_id=challenge_id,
				send_mode="bulk",
				provider_status=cint((bulk_data or {}).get("status")),
				provider_message=(bulk_data or {}).get("message"),
				line_number=line_number,
				request_payload=safe_payload,
				response_payload=bulk_data,
			)
			frappe.throw((bulk_data or {}).get("message") or _("SMS provider rejected OTP request."))
		provider_ref = ""
		if isinstance((bulk_data or {}).get("data"), dict):
			provider_ref = str((bulk_data or {}).get("data", {}).get("packId") or "")
		_log_mobile_otp_event(
			event_type="sms_sent",
			mobile=mobile,
			user=user,
			challenge_id=challenge_id,
			send_mode="bulk",
			provider_status=cint((bulk_data or {}).get("status")),
			provider_message=(bulk_data or {}).get("message"),
			provider_reference=provider_ref,
			line_number=line_number,
			request_payload=safe_payload,
			response_payload=bulk_data,
		)
	except Exception:
		_log_mobile_otp_event(
			event_type="sms_failed",
			mobile=mobile,
			user=user,
			challenge_id=challenge_id,
			send_mode="bulk",
			line_number=line_number,
			request_payload=safe_payload,
			error=frappe.get_traceback(),
		)
		raise


def _send_verify_sms(mobile: str, otp_code: str, user: str, challenge_id: str):
	ss = frappe.get_doc("SMS Settings", "SMS Settings")
	gateway_url = (ss.sms_gateway_url or "").strip().lower()
	if not gateway_url.endswith("/v1/send/verify"):
		frappe.throw(_("SMS gateway URL must be set to /v1/send/verify for mobile OTP login."))

	headers = get_headers(ss)
	headers.setdefault("Accept", "application/json")
	headers.setdefault("Content-Type", "application/json")

	template_id, parameter_name = _get_verify_template_settings(ss)
	if not template_id:
		_log_mobile_otp_event(
			event_type="sms_failed",
			mobile=mobile,
			user=user,
			challenge_id=challenge_id,
			send_mode="verify",
			error="Missing templateId in SMS Settings for verify flow",
		)
		frappe.throw(
			_(
				"OTP Verify template is not configured. Add a valid templateId in SMS Settings static parameters."
			)
		)

	verify_payload = {
		"mobile": mobile,
		"templateId": template_id,
		"parameters": [{"name": parameter_name, "value": otp_code}],
	}
	safe_payload = {
		"mobile": mobile,
		"templateId": template_id,
		"parameters": [{"name": parameter_name, "value": "OTP_CODE"}],
	}

	try:
		verify_response = requests.post(ss.sms_gateway_url, json=verify_payload, headers=headers, timeout=15)
		verify_response.raise_for_status()
		verify_data = verify_response.json() if verify_response.content else {}

		if cint((verify_data or {}).get("status")) != 1:
			_log_mobile_otp_event(
				event_type="sms_failed",
				mobile=mobile,
				user=user,
				challenge_id=challenge_id,
				send_mode="verify",
				provider_status=cint((verify_data or {}).get("status")),
				provider_message=(verify_data or {}).get("message"),
				template_id=template_id,
				request_payload=safe_payload,
				response_payload=verify_data,
			)
			error_message = (verify_data or {}).get("message") or _("SMS provider rejected OTP request.")
			frappe.throw(error_message)

		provider_ref = ""
		if isinstance((verify_data or {}).get("data"), dict):
			provider_ref = str((verify_data or {}).get("data", {}).get("messageId") or "")
		_log_mobile_otp_event(
			event_type="sms_sent",
			mobile=mobile,
			user=user,
			challenge_id=challenge_id,
			send_mode="verify",
			provider_status=cint((verify_data or {}).get("status")),
			provider_message=(verify_data or {}).get("message"),
			provider_reference=provider_ref,
			template_id=template_id,
			request_payload=safe_payload,
			response_payload=verify_data,
		)
	except Exception:
		_log_mobile_otp_event(
			event_type="sms_failed",
			mobile=mobile,
			user=user,
			challenge_id=challenge_id,
			send_mode="verify",
			template_id=template_id,
			request_payload=safe_payload,
			error=frappe.get_traceback(),
		)
		raise


def _validate_mobile_login_is_enabled():
	if not cint(frappe.db.get_single_value("System Settings", "allow_login_using_mobile_number")):
		frappe.throw(_("Mobile login is disabled by System Settings."))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60)
def send_mobile_login_otp(mobile: str):
	_validate_mobile_login_is_enabled()

	normalized_mobile = _normalize_mobile(mobile)
	if not normalized_mobile:
		frappe.throw(_("Enter a valid mobile number."))

	user = _find_user_by_mobile(normalized_mobile)
	if not user:
		frappe.throw(_("No active user found with this mobile number."))

	remaining_cooldown = _remaining_cooldown_seconds(normalized_mobile)
	if remaining_cooldown:
		active_challenge_id = _get_active_challenge_id(normalized_mobile)
		if active_challenge_id:
			active_challenge = _load_challenge(active_challenge_id)
			if active_challenge and active_challenge.get("user") == user:
				return {
					"sent": False,
					"cooldown": True,
					"challenge_id": active_challenge_id,
					"retry_after": remaining_cooldown,
					"expires_in": OTP_EXPIRY_SECONDS,
					"masked_mobile": normalized_mobile[:4] + "******" + normalized_mobile[-1:],
					"message": _("A code has already been sent. Please wait before requesting another code."),
				}
			_clear_active_challenge_id(normalized_mobile)

	otp_code = f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"
	challenge_id = frappe.generate_hash(length=24)
	challenge = {
		"user": user,
		"mobile": normalized_mobile,
		"otp_hash": _hash_otp(normalized_mobile, otp_code),
		"attempts": 0,
	}

	_send_verify_sms(normalized_mobile, otp_code, user, challenge_id)
	_save_challenge(challenge_id, challenge, expires_in_sec=OTP_EXPIRY_SECONDS)
	_save_active_challenge_id(normalized_mobile, challenge_id)
	frappe.cache.set_value(
		_cooldown_key(normalized_mobile),
		int(time.time()) + OTP_RESEND_COOLDOWN_SECONDS,
		expires_in_sec=OTP_RESEND_COOLDOWN_SECONDS,
	)

	return {
		"sent": True,
		"challenge_id": challenge_id,
		"expires_in": OTP_EXPIRY_SECONDS,
		"masked_mobile": normalized_mobile[:4] + "******" + normalized_mobile[-1:],
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=100, seconds=60 * 60)
def login_via_mobile_otp(mobile: str, otp: str, challenge_id: str):
	_validate_mobile_login_is_enabled()

	normalized_mobile = _normalize_mobile(mobile)
	if not normalized_mobile:
		frappe.throw(_("Enter a valid mobile number."))

	if not otp or not challenge_id:
		frappe.throw(_("Verification code and challenge are required."))

	challenge = _load_challenge(challenge_id)
	if not challenge:
		_log_mobile_otp_event(
			event_type="otp_failed",
			mobile=normalized_mobile,
			challenge_id=challenge_id,
			error="Challenge missing or expired",
		)
		frappe.throw(_("Verification session expired. Please request a new code."))

	if challenge.get("mobile") != normalized_mobile:
		_delete_challenge(challenge_id)
		_clear_active_challenge_id(normalized_mobile, challenge_id=challenge_id)
		_log_mobile_otp_event(
			event_type="otp_failed",
			mobile=normalized_mobile,
			user=challenge.get("user"),
			challenge_id=challenge_id,
			error="Mobile mismatch",
		)
		frappe.throw(_("Mobile number mismatch. Please request a new code."))

	attempts = cint(challenge.get("attempts"))
	if attempts >= OTP_MAX_ATTEMPTS:
		_delete_challenge(challenge_id)
		_clear_active_challenge_id(normalized_mobile, challenge_id=challenge_id)
		_log_mobile_otp_event(
			event_type="otp_failed",
			mobile=normalized_mobile,
			user=challenge.get("user"),
			challenge_id=challenge_id,
			error="Max attempts reached",
		)
		frappe.throw(_("Too many attempts. Please request a new code."))

	if _hash_otp(normalized_mobile, otp.strip()) != challenge.get("otp_hash"):
		challenge["attempts"] = attempts + 1
		_save_challenge(challenge_id, challenge, expires_in_sec=OTP_EXPIRY_SECONDS)
		if challenge["attempts"] >= OTP_MAX_ATTEMPTS:
			_delete_challenge(challenge_id)
			_clear_active_challenge_id(normalized_mobile, challenge_id=challenge_id)
		_log_mobile_otp_event(
			event_type="otp_failed",
			mobile=normalized_mobile,
			user=challenge.get("user"),
			challenge_id=challenge_id,
			error=f"Invalid OTP attempt {challenge['attempts']}",
		)
		frappe.throw(_("Incorrect verification code."))

	user = challenge.get("user")
	if not user or not frappe.db.get_value("User", user, "enabled"):
		_delete_challenge(challenge_id)
		_clear_active_challenge_id(normalized_mobile, challenge_id=challenge_id)
		_log_mobile_otp_event(
			event_type="otp_failed",
			mobile=normalized_mobile,
			user=user,
			challenge_id=challenge_id,
			error="User disabled or missing",
		)
		frappe.throw(_("User is disabled or missing."))

	_delete_challenge(challenge_id)
	_clear_active_challenge_id(normalized_mobile, challenge_id=challenge_id)

	frappe.local.login_manager = LoginManager()
	frappe.local.login_manager.login_as(user)
	_log_mobile_otp_event(
		event_type="otp_verified",
		mobile=normalized_mobile,
		user=user,
		challenge_id=challenge_id,
	)

	return {
		"logged_in": True,
		"message": frappe.local.response.get("message"),
		"home_page": frappe.local.response.get("home_page"),
		"redirect_to": frappe.local.response.get("redirect_to"),
		"full_name": frappe.response.get("full_name"),
	}
