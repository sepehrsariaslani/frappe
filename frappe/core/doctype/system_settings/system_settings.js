const SYSTEM_THEME_COLOR_FIELDS = [
	"system_theme_primary_light",
	"system_theme_background_light",
	"system_theme_surface_light",
	"system_theme_text_light",
	"system_theme_text_muted_light",
	"system_theme_border_light",
	"system_theme_control_bg_light",
	"system_theme_navbar_bg_light",
	"system_theme_success_light",
	"system_theme_warning_light",
	"system_theme_danger_light",
	"system_theme_info_light",
	"system_theme_primary_dark",
	"system_theme_background_dark",
	"system_theme_surface_dark",
	"system_theme_text_dark",
	"system_theme_text_muted_dark",
	"system_theme_border_dark",
	"system_theme_control_bg_dark",
	"system_theme_navbar_bg_dark",
	"system_theme_success_dark",
	"system_theme_warning_dark",
	"system_theme_danger_dark",
	"system_theme_info_dark",
];

const SYSTEM_THEME_TOGGLED_FIELDS = [
	"system_theme_preset",
	"system_theme_reset_colors",
	"system_theme_preview",
	"system_theme_light_section",
	...SYSTEM_THEME_COLOR_FIELDS.slice(0, 12),
	"system_theme_dark_section",
	...SYSTEM_THEME_COLOR_FIELDS.slice(12),
];

const SYSTEM_THEME_PRESETS = {
	Default: {
		light: {
			primary: "#171717",
			background: "#FFFFFF",
			surface: "#FFFFFF",
			text: "#383838",
			text_muted: "#7C7C7C",
			border: "#EDEDED",
			control_bg: "#F3F3F3",
			navbar_bg: "#FFFFFF",
			success: "#30A66D",
			warning: "#D1930D",
			danger: "#CC2929",
			info: "#007BE0",
		},
		dark: {
			primary: "#E2E2E2",
			background: "#171717",
			surface: "#171717",
			text: "#F8F8F8",
			text_muted: "#C7C7C7",
			border: "#383838",
			control_bg: "#383838",
			navbar_bg: "#171717",
			success: "#59BA8B",
			warning: "#F2BE3A",
			danger: "#EB9091",
			info: "#70B6F0",
		},
	},
	Ocean: {
		light: {
			primary: "#0A5EA8",
			background: "#F4FAFF",
			surface: "#FFFFFF",
			text: "#11324A",
			text_muted: "#4B6B82",
			border: "#CFE3F3",
			control_bg: "#E8F2FA",
			navbar_bg: "#EAF5FF",
			success: "#1D8F6C",
			warning: "#D7951A",
			danger: "#C74848",
			info: "#0A78D1",
		},
		dark: {
			primary: "#8FCBFF",
			background: "#0D1B2A",
			surface: "#13253A",
			text: "#E1F0FF",
			text_muted: "#A9C3DA",
			border: "#28405A",
			control_bg: "#1B3148",
			navbar_bg: "#12263B",
			success: "#48C9A9",
			warning: "#F4BE63",
			danger: "#F28080",
			info: "#5DB5FF",
		},
	},
	Emerald: {
		light: {
			primary: "#1F7A4D",
			background: "#F3FCF7",
			surface: "#FFFFFF",
			text: "#143626",
			text_muted: "#4A705D",
			border: "#CDE5D8",
			control_bg: "#E5F3EB",
			navbar_bg: "#EAF7F0",
			success: "#22965E",
			warning: "#C79C1D",
			danger: "#C25151",
			info: "#2E7DB2",
		},
		dark: {
			primary: "#8AE0B4",
			background: "#11251B",
			surface: "#173126",
			text: "#DCF6E7",
			text_muted: "#A0C8B0",
			border: "#2A4A3B",
			control_bg: "#234236",
			navbar_bg: "#1A352A",
			success: "#66D79E",
			warning: "#E7C16A",
			danger: "#EB8A8A",
			info: "#78B8E8",
		},
	},
	Sunset: {
		light: {
			primary: "#A33A2A",
			background: "#FFF8F5",
			surface: "#FFFFFF",
			text: "#4A2018",
			text_muted: "#7A5148",
			border: "#E8CFC8",
			control_bg: "#F5E3DE",
			navbar_bg: "#FDEEE9",
			success: "#2E8B57",
			warning: "#D28D1F",
			danger: "#C44747",
			info: "#2B74B8",
		},
		dark: {
			primary: "#FFB8A7",
			background: "#241815",
			surface: "#30211D",
			text: "#F7E6E2",
			text_muted: "#D2B3AB",
			border: "#5A3D37",
			control_bg: "#4A322D",
			navbar_bg: "#2E201C",
			success: "#7DD39D",
			warning: "#F0C276",
			danger: "#F29A9A",
			info: "#8CC1F0",
		},
	},
};

function has_system_theme_fields(frm) {
	return Boolean(frm?.fields_dict?.system_theme_enabled);
}

function get_theme_value(frm, fieldname, fallback) {
	const value = frm.doc[fieldname];
	return value && typeof value === "string" ? value : fallback;
}

function get_active_theme_preset(frm) {
	const preset = frm.doc.system_theme_preset;
	return SYSTEM_THEME_PRESETS[preset] ? preset : "Default";
}

function get_preset_values(preset) {
	const selected = SYSTEM_THEME_PRESETS[preset] || SYSTEM_THEME_PRESETS.Default;
	const values = {};

	["light", "dark"].forEach((mode) => {
		Object.entries(selected[mode]).forEach(([key, color]) => {
			values[`system_theme_${key}_${mode}`] = color;
		});
	});

	return values;
}

function apply_theme_preset(frm, show_alert = false) {
	const values = get_preset_values(get_active_theme_preset(frm));
	const updates = {};

	Object.keys(values).forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			updates[fieldname] = values[fieldname];
		}
	});

	if (!Object.keys(updates).length) return;

	frm.set_value(updates);
	if (show_alert) {
		frappe.show_alert({
			message: __("Preset colors loaded"),
			indicator: "green",
		});
	}
}

frappe.ui.form.on("System Settings", {
	refresh: function (frm) {
		frappe.call({
			method: "frappe.core.doctype.system_settings.system_settings.load",
			callback: function (data) {
				frappe.all_timezones = data.message.timezones;
				frm.set_df_property("time_zone", "options", frappe.all_timezones);

				$.each(data.message.defaults, function (key, val) {
					frm.set_value(key, val, null, true);
					frappe.sys_defaults[key] = val;
				});
				if (frm.re_setup_moment) {
					frappe.app.setup_moment();
					delete frm.re_setup_moment;
				}
			},
		});

		frappe.xcall("frappe.apps.get_apps").then((r) => {
			let apps = r?.map((r) => r.name) || [];
			frm.set_df_property("default_app", "options", [" ", ...apps]);
		});

		frm.trigger("set_rounding_method_options");
		frm.trigger("toggle_system_theme_fields");
		frm.trigger("set_system_theme_preview");
	},
	enable_password_policy: function (frm) {
		if (frm.doc.enable_password_policy == 0) {
			frm.set_value("minimum_password_score", "");
		} else {
			frm.set_value("minimum_password_score", "2");
		}
	},
	enable_two_factor_auth: function (frm) {
		if (frm.doc.enable_two_factor_auth == 0) {
			frm.set_value("bypass_2fa_for_retricted_ip_users", 0);
			frm.set_value("bypass_restrict_ip_check_if_2fa_enabled", 0);
		}
	},
	after_save: function (frm) {
		/**
		 * Checks whether the effective value has changed.
		 *
		 * @param {Array.<string>} - Tuple with new fallback, previous fallback and
		 *   optionally an override value.
		 * @returns {boolean} - Whether the resulting value has effectively changed
		 */
		const has_effectively_changed = ([new_fallback, prev_fallback, override = undefined]) =>
			!override && prev_fallback !== new_fallback;

		const attr_tuples = [
			[frm.doc.language, frappe.boot.sysdefaults.language, frappe.boot.user.language],
			[frm.doc.rounding_method, frappe.boot.sysdefaults.rounding_method], // no user override.
		];

		if (attr_tuples.some(has_effectively_changed)) {
			frappe.msgprint(__("Refreshing..."));
			window.location.reload();
		}
	},
	first_day_of_the_week(frm) {
		frm.re_setup_moment = true;
	},

	rounding_method: function (frm) {
		if (frm.doc.rounding_method == frappe.boot.sysdefaults.rounding_method) return;
		let msg = __(
			"Changing rounding method on site with data can result in unexpected behaviour."
		);
		msg += "<br>";
		msg += __("Do you still want to proceed?");

		frappe.confirm(
			msg,
			() => {},
			() => {
				frm.set_value("rounding_method", frappe.boot.sysdefaults.rounding_method);
			}
		);
	},

	set_rounding_method_options: function (frm) {
		if (frm.doc.rounding_method != "Banker's Rounding (legacy)") {
			let field = frm.fields_dict.rounding_method;

			field.df.options = field.df.options
				.split("\n")
				.filter((o) => o != "Banker's Rounding (legacy)")
				.join("\n");

			field.refresh();
		}
	},
	toggle_system_theme_fields: function (frm) {
		if (!has_system_theme_fields(frm)) return;

		const enabled = !!frm.doc.system_theme_enabled;
		SYSTEM_THEME_TOGGLED_FIELDS.forEach((fieldname) => {
			if (frm.fields_dict[fieldname]) {
				frm.set_df_property(fieldname, "hidden", !enabled);
			}
		});
	},
	system_theme_enabled: function (frm) {
		frm.trigger("toggle_system_theme_fields");
		frm.trigger("set_system_theme_preview");
	},
	system_theme_preset: function (frm) {
		apply_theme_preset(frm);
		frm.trigger("set_system_theme_preview");
	},
	system_theme_reset_colors: function (frm) {
		if (!frm.doc.system_theme_preset) {
			frappe.msgprint(__("Please choose a preset first."));
			return;
		}

		apply_theme_preset(frm, true);
		frm.trigger("set_system_theme_preview");
	},
	set_system_theme_preview: function (frm) {
		if (!has_system_theme_fields(frm) || !frm.fields_dict.system_theme_preview) return;

		if (!frm.doc.system_theme_enabled) {
			frm.set_df_property(
				"system_theme_preview",
				"options",
				`<div class="text-muted">${__("Theme manager is disabled.")}</div>`
			);
			return;
		}

		const preview_fallback = get_preset_values(get_active_theme_preset(frm));

		const light = {
			primary: get_theme_value(
				frm,
				"system_theme_primary_light",
				preview_fallback.system_theme_primary_light
			),
			background: get_theme_value(
				frm,
				"system_theme_background_light",
				preview_fallback.system_theme_background_light
			),
			text: get_theme_value(frm, "system_theme_text_light", preview_fallback.system_theme_text_light),
			surface: get_theme_value(
				frm,
				"system_theme_surface_light",
				preview_fallback.system_theme_surface_light
			),
		};

		const dark = {
			primary: get_theme_value(
				frm,
				"system_theme_primary_dark",
				preview_fallback.system_theme_primary_dark
			),
			background: get_theme_value(
				frm,
				"system_theme_background_dark",
				preview_fallback.system_theme_background_dark
			),
			text: get_theme_value(frm, "system_theme_text_dark", preview_fallback.system_theme_text_dark),
			surface: get_theme_value(
				frm,
				"system_theme_surface_dark",
				preview_fallback.system_theme_surface_dark
			),
		};

		const preview_html = `
			<div style="display:flex; gap:16px; flex-wrap:wrap;">
				<div style="border:1px solid #d1d8dd; border-radius:8px; overflow:hidden; min-width:220px;">
					<div style="background:${light.primary}; color:#fff; padding:8px 10px; font-size:12px;">${__(
			"Light"
		)}</div>
					<div style="background:${light.background}; color:${light.text}; padding:10px;">
						<div style="background:${light.surface}; border:1px solid #d1d8dd; border-radius:6px; padding:8px;">
							${__("Primary")}: <span style="color:${light.primary}; font-weight:600;">${light.primary}</span>
						</div>
					</div>
				</div>
				<div style="border:1px solid #d1d8dd; border-radius:8px; overflow:hidden; min-width:220px;">
					<div style="background:${dark.primary}; color:#111; padding:8px 10px; font-size:12px;">${__(
			"Dark"
		)}</div>
					<div style="background:${dark.background}; color:${dark.text}; padding:10px;">
						<div style="background:${dark.surface}; border:1px solid #4d4d4d; border-radius:6px; padding:8px;">
							${__("Primary")}: <span style="color:${dark.primary}; font-weight:600;">${dark.primary}</span>
						</div>
					</div>
				</div>
			</div>
		`;

		frm.set_df_property("system_theme_preview", "options", preview_html);
	},
});

SYSTEM_THEME_COLOR_FIELDS.forEach((fieldname) => {
	frappe.ui.form.on("System Settings", fieldname, function (frm) {
		frm.trigger("set_system_theme_preview");
	});
});
