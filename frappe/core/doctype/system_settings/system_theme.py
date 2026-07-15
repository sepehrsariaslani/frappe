# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

from __future__ import annotations

import os
import re
from datetime import datetime

import frappe
from frappe.utils import cint

THEME_FILE_NAME = "frappe_system_theme.css"
DEFAULT_PRESET = "Default"

COLOR_KEYS = (
	"primary",
	"background",
	"surface",
	"text",
	"text_muted",
	"border",
	"control_bg",
	"navbar_bg",
	"success",
	"warning",
	"danger",
	"info",
)

HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")

PRESETS = {
	"Default": {
		"light": {
			"primary": "#171717",
			"background": "#FFFFFF",
			"surface": "#FFFFFF",
			"text": "#383838",
			"text_muted": "#7C7C7C",
			"border": "#EDEDED",
			"control_bg": "#F3F3F3",
			"navbar_bg": "#FFFFFF",
			"success": "#30A66D",
			"warning": "#D1930D",
			"danger": "#CC2929",
			"info": "#007BE0",
		},
		"dark": {
			"primary": "#E2E2E2",
			"background": "#171717",
			"surface": "#171717",
			"text": "#F8F8F8",
			"text_muted": "#C7C7C7",
			"border": "#383838",
			"control_bg": "#383838",
			"navbar_bg": "#171717",
			"success": "#59BA8B",
			"warning": "#F2BE3A",
			"danger": "#EB9091",
			"info": "#70B6F0",
		},
	},
	"Ocean": {
		"light": {
			"primary": "#0A5EA8",
			"background": "#F4FAFF",
			"surface": "#FFFFFF",
			"text": "#11324A",
			"text_muted": "#4B6B82",
			"border": "#CFE3F3",
			"control_bg": "#E8F2FA",
			"navbar_bg": "#EAF5FF",
			"success": "#1D8F6C",
			"warning": "#D7951A",
			"danger": "#C74848",
			"info": "#0A78D1",
		},
		"dark": {
			"primary": "#8FCBFF",
			"background": "#0D1B2A",
			"surface": "#13253A",
			"text": "#E1F0FF",
			"text_muted": "#A9C3DA",
			"border": "#28405A",
			"control_bg": "#1B3148",
			"navbar_bg": "#12263B",
			"success": "#48C9A9",
			"warning": "#F4BE63",
			"danger": "#F28080",
			"info": "#5DB5FF",
		},
	},
	"Emerald": {
		"light": {
			"primary": "#1F7A4D",
			"background": "#F3FCF7",
			"surface": "#FFFFFF",
			"text": "#143626",
			"text_muted": "#4A705D",
			"border": "#CDE5D8",
			"control_bg": "#E5F3EB",
			"navbar_bg": "#EAF7F0",
			"success": "#22965E",
			"warning": "#C79C1D",
			"danger": "#C25151",
			"info": "#2E7DB2",
		},
		"dark": {
			"primary": "#8AE0B4",
			"background": "#11251B",
			"surface": "#173126",
			"text": "#DCF6E7",
			"text_muted": "#A0C8B0",
			"border": "#2A4A3B",
			"control_bg": "#234236",
			"navbar_bg": "#1A352A",
			"success": "#66D79E",
			"warning": "#E7C16A",
			"danger": "#EB8A8A",
			"info": "#78B8E8",
		},
	},
	"Sunset": {
		"light": {
			"primary": "#A33A2A",
			"background": "#FFF8F5",
			"surface": "#FFFFFF",
			"text": "#4A2018",
			"text_muted": "#7A5148",
			"border": "#E8CFC8",
			"control_bg": "#F5E3DE",
			"navbar_bg": "#FDEEE9",
			"success": "#2E8B57",
			"warning": "#D28D1F",
			"danger": "#C44747",
			"info": "#2B74B8",
		},
		"dark": {
			"primary": "#FFB8A7",
			"background": "#241815",
			"surface": "#30211D",
			"text": "#F7E6E2",
			"text_muted": "#D2B3AB",
			"border": "#5A3D37",
			"control_bg": "#4A322D",
			"navbar_bg": "#2E201C",
			"success": "#7DD39D",
			"warning": "#F0C276",
			"danger": "#F29A9A",
			"info": "#8CC1F0",
		},
	},
}


def _normalize_hex_color(value: str | None) -> str | None:
	if not value:
		return None

	value = str(value).strip()
	if not HEX_COLOR_PATTERN.match(value):
		return None

	if len(value) == 4:
		value = "#" + "".join(ch * 2 for ch in value[1:])

	return value.upper()


def _hex_to_rgba(hex_color: str | None, alpha: float) -> str:
	normalized = _normalize_hex_color(hex_color)
	if not normalized:
		return "rgba(0, 0, 0, 0)"

	red = int(normalized[1:3], 16)
	green = int(normalized[3:5], 16)
	blue = int(normalized[5:7], 16)
	return f"rgba({red}, {green}, {blue}, {alpha})"


def _get_preset_or_default(preset_name: str | None) -> dict:
	return PRESETS.get(preset_name) or PRESETS[DEFAULT_PRESET]


def _resolve_theme_palette(doc) -> dict:
	preset_name = doc.get("system_theme_preset") or DEFAULT_PRESET
	preset = _get_preset_or_default(preset_name)

	resolved = {
		"enabled": cint(doc.get("system_theme_enabled")),
		"preset": preset_name,
		"light": {},
		"dark": {},
	}

	for mode in ("light", "dark"):
		for key in COLOR_KEYS:
			fieldname = f"system_theme_{key}_{mode}"
			value = _normalize_hex_color(doc.get(fieldname))
			resolved[mode][key] = value or preset[mode][key]

	return resolved


def _build_mode_variables(palette: dict) -> dict[str, str]:
	primary = palette["primary"]
	background = palette["background"]
	surface = palette["surface"]
	text = palette["text"]
	text_muted = palette["text_muted"]
	border = palette["border"]
	control_bg = palette["control_bg"]

	return {
		"--primary": primary,
		"--primary-color": primary,
		"--brand-color": primary,
		"--bg-color": background,
		"--background-light": background,
		"--background-dark": background,
		"--fg-color": surface,
		"--card-bg": surface,
		"--navbar-bg": palette["navbar_bg"],
		"--secondary-color": control_bg,
		"--accent-color": primary,
		"--text-color": text,
		"--heading-color": text,
		"--text-muted": text_muted,
		"--text-light": text_muted,
		"--text-dark": text,
		"--border-color": border,
		"--table-border-color": border,
		"--dark-border-color": border,
		"--border-primary": border,
		"--control-bg": control_bg,
		"--control-bg-on-gray": control_bg,
		"--disabled-control-bg": _hex_to_rgba(control_bg, 0.8),
		"--scroll-bg": background,
		"--scroll-color": border,
		"--btn-primary": primary,
		"--btn-default-bg": control_bg,
		"--btn-default-hover-bg": _hex_to_rgba(control_bg, 0.85),
		"--sidebar-select-color": _hex_to_rgba(primary, 0.14),
		"--scrollbar-thumb-color": border,
		"--scrollbar-track-color": background,
		"--success-color": palette["success"],
		"--warning-color": palette["warning"],
		"--danger-color": palette["danger"],
		"--info-color": palette["info"],
		"--alert-text-success": palette["success"],
		"--alert-text-warning": palette["warning"],
		"--alert-text-danger": palette["danger"],
		"--alert-text-info": palette["info"],
		"--alert-bg-success": _hex_to_rgba(palette["success"], 0.16),
		"--alert-bg-warning": _hex_to_rgba(palette["warning"], 0.18),
		"--alert-bg-danger": _hex_to_rgba(palette["danger"], 0.16),
		"--alert-bg-info": _hex_to_rgba(palette["info"], 0.16),
		"--highlight-color": _hex_to_rgba(primary, 0.08),
	}


def _build_css(settings: dict) -> str:
	generated_on = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

	if not settings["enabled"]:
		return (
			"/* This file is auto-generated by Frappe.\n"
			f"   Generated: {generated_on}\n"
			"   Theme manager is disabled. */\n"
		)

	light_variables = _build_mode_variables(settings["light"])
	dark_variables = _build_mode_variables(settings["dark"])

	def render_rule(selector: str, variables: dict[str, str]) -> str:
		lines = [f"{selector} {{"]
		lines.extend(f"\t{key}: {value} !important;" for key, value in variables.items())
		lines.append("}")
		return "\n".join(lines)

	css_rules = [
		"/* This file is auto-generated by Frappe. */",
		f"/* Generated: {generated_on} */",
		f"/* Active preset: {settings['preset']} */",
		render_rule(":root, [data-theme=\"light\"]", light_variables),
		render_rule("[data-theme=\"dark\"]", dark_variables),
	]

	return "\n\n".join(css_rules) + "\n"


def _write_css_file(content: str):
	output_path = frappe.get_site_path("public", "files", THEME_FILE_NAME)
	os.makedirs(os.path.dirname(output_path), exist_ok=True)

	with open(output_path, "w", encoding="utf-8") as css_file:
		css_file.write(content)


def generate_system_theme_css(doc=None, method=None):
	"""Generate site-level UI theme css from System Settings."""
	settings_doc = doc or frappe.get_single("System Settings")
	palette = _resolve_theme_palette(settings_doc)
	css_content = _build_css(palette)
	_write_css_file(css_content)


def get_theme_preset_values(preset: str | None = None) -> dict[str, str]:
	preset_name = preset or DEFAULT_PRESET
	preset_data = _get_preset_or_default(preset_name)

	response = {}
	for mode in ("light", "dark"):
		for key in COLOR_KEYS:
			response[f"system_theme_{key}_{mode}"] = preset_data[mode][key]

	return response
