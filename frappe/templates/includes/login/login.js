// login.js
// don't remove this line (used in test)

window.disable_signup = {{ disable_signup and "true" or "false" }};
window.show_footer_on_login = {{ show_footer_on_login and "true" or "false" }};

window.login = {};

window.verify = {};

login.bind_events = function () {
	$(window).on("hashchange", function () {
		login.route();
	});

	$(".form-login").on("submit", function (event) {
		event.preventDefault();
		var args = {};
		args.cmd = "login";
		args.usr = ($("#login_email").val() || "").trim();
		args.pwd = $("#login_password").val();
		if (!args.usr || !args.pwd) {
			{# striptags is used to remove newlines, e is used for escaping #}
			frappe.msgprint("{{ _('Both login and password required') | striptags | e }}");
			return false;
		}
		login.call(args, null, "/login");
		return false;
	});

	$(".form-signup").on("submit", function (event) {
		event.preventDefault();
		var args = {};
		args.cmd = "frappe.core.doctype.user.user.sign_up";
		args.email = ($("#signup_email").val() || "").trim();
		args.redirect_to = frappe.utils.sanitise_redirect(frappe.utils.get_url_arg("redirect-to"));
		args.full_name = frappe.utils.xss_sanitise(($("#signup_fullname").val() || "").trim());
		if (!args.email || !validate_email(args.email) || !args.full_name) {
			login.set_status({{ _("Valid email and name required") | tojson }}, 'red');
			return false;
		}
		login.call(args);
		return false;
	});

	$(".form-forgot").on("submit", function (event) {
		event.preventDefault();
		var args = {};
		args.cmd = "frappe.core.doctype.user.user.reset_password";
		args.user = ($("#forgot_email").val() || "").trim();
		if (!args.user) {
			login.set_status({{ _("Valid Login id required.") | tojson }}, 'red');
			return false;
		}
		login.call(args);
		return false;
	});

	$(".form-login-with-email-link").on("submit", function (event) {
		event.preventDefault();
		var args = {};
		args.cmd = "frappe.www.login.send_login_link";
		args.email = ($("#login_with_email_link_email").val() || "").trim();
		if (!args.email) {
			login.set_status({{ _("Valid Login id required.") | tojson }}, 'red');
			return false;
		}
		login.call(args).then(() => {
			login.set_status({{ _("Login link sent to your email") | tojson }}, 'blue');
			$("#login_with_email_link_email").val("");
		}).catch(() => {
			login.set_status({{ _("Send login link") | tojson }}, 'blue');
		});

		return false;
	});

	$(".toggle-password").click(function () {
		var input = $($(this).attr("toggle"));
		if (input.attr("type") == "password") {
			input.attr("type", "text");
			$(this).text("پنهان")
		} else {
			input.attr("type", "password");
			$(this).text("نمایش")
		}
	});

	{% if ldap_settings and ldap_settings.enabled %}
	$(".btn-ldap-login").on("click", function () {
		var args = {};
		args.cmd = "{{ ldap_settings.method }}";
		args.usr = ($("#login_email").val() || "").trim();
		args.pwd = $("#login_password").val();
		if (!args.usr || !args.pwd) {
			login.set_status({{ _("Both login and password required") | tojson }}, 'red');
			return false;
		}
		login.call(args);
		return false;
	});
	{% endif %}
}


login.route = function () {
	var route = window.location.hash.slice(1);
	if (!route) route = "login";
	route = route.replaceAll("-", "_");
	login[route]();
}

login.reset_sections = function (hide) {
	if (hide || hide === undefined) {
		$("section.for-login").toggle(false);
		$("section.for-email-login").toggle(false);
		$("section.for-forgot").toggle(false);
		$("section.for-login-with-email-link").toggle(false);
		$("section.for-signup").toggle(false);
	}
	$('section:not(.signup-disabled) .indicator').each(function () {
		$(this).removeClass().addClass('indicator').addClass('blue')
			.text($(this).attr('data-text'));
	});
}

login.login = function () {
	login.reset_sections();
	$(".for-login").toggle(true);
}

login.email = function () {
	login.reset_sections();
	$(".for-email-login").toggle(true);
	$("#login_email").focus();
}

login.steptwo = function () {
	login.reset_sections();
	$(".for-login").toggle(true);
	$("#login_email").focus();
}

login.forgot = function () {
	login.reset_sections();
	if ($("#login_email").val()) {
		$("#forgot_email").val($("#login_email").val());
	}
	$(".for-forgot").toggle(true);
	$("#forgot_email").focus();
}

login.login_with_email_link = function () {
	login.reset_sections();
	if ($("#login_email").val()) {
		$("#login_with_email_link_email").val($("#login_email").val());
	}
	$(".for-login-with-email-link").toggle(true);
	$("#login_with_email_link_email").focus();
}

login.signup = function () {
	login.reset_sections();
	$(".for-signup").toggle(true);
	$("#signup_fullname").focus();
}


// Login
login.call = function (args, callback, url="/") {
	login.set_status({{ _("Verifying...") | tojson }}, 'blue');

	return frappe.call({
		type: "POST",
		url: url,
		args: args,
		callback: callback,
		freeze: true,
		statusCode: login.login_handlers
	});
}

login.set_status = function (message, color) {
	$('section:visible .btn-primary').text(message)
	if (color == "red") {
		$('section:visible .page-card-body').addClass("invalid");
	}
}

login.set_invalid = function (message) {
	$(".login-content.page-card").addClass('invalid-login');
	setTimeout(() => {
		$(".login-content.page-card").removeClass('invalid-login');
	}, 500)
	login.set_status(message, 'red');
	$("#login_password").focus();
}

login.login_handlers = (function () {
	var get_error_handler = function (default_message) {
		return function (xhr, data) {
			if (xhr.responseJSON) {
				data = xhr.responseJSON;
			}

			var message = default_message;
			if (data._server_messages) {
				message = ($.map(JSON.parse(data._server_messages || '[]'), function (v) {
					// temp fix for messages sent as dict
					try {
						return JSON.parse(v).message;
					} catch (e) {
						return v;
					}
				}) || []).join('<br>') || default_message;
			}

			login.set_invalid(default_message);
			if (message !== default_message) {
				login.reset_sections(false);
			}
		};
	}

	var login_handlers = {
		200: function (data) {
			if (data.message == 'Logged In') {
				login.set_status({{ _("Success") | tojson }}, 'green');
				document.body.innerHTML = `{% include "templates/includes/splash_screen.html" %}`;
				window.location.href = frappe.utils.sanitise_redirect(frappe.utils.get_url_arg("redirect-to")) || data.home_page;
			} else if (data.message == 'Password Reset') {
				window.location.href = frappe.utils.sanitise_redirect(data.redirect_to);
			} else if (data.message == "No App") {
				login.set_status({{ _("Success") | tojson }}, 'green');
				if (localStorage) {
					var last_visited =
						localStorage.getItem("last_visited")
						|| frappe.utils.sanitise_redirect(frappe.utils.get_url_arg("redirect-to"));
					localStorage.removeItem("last_visited");
				}

				if (data.redirect_to) {
					window.location.href = frappe.utils.sanitise_redirect(data.redirect_to);
				}

				if (last_visited && last_visited != "/login") {
					window.location.href = last_visited;
				} else {
					window.location.href = data.home_page;
				}
			} else if (window.location.hash === '#forgot') {
				// Always show the same message regardless of whether the account
				// exists or not, to prevent username enumeration (CWE-204).
				login.set_status({{ _("Instructions Emailed") | tojson }}, 'green');
			} else if (window.location.hash === '#signup') {
				if (cint(data.message[0]) == 0) {
					login.set_status(data.message[1], 'red');
				} else {
					login.set_status({{ _("Success") | tojson }}, 'green');
					frappe.msgprint(data.message[1])
				}
				//login.set_status(__(data.message), 'green');
			}

			//OTP verification
			if (data.verification && data.message != 'Logged In') {
				login.set_status({{ _("Success") | tojson }}, 'green');

				document.cookie = "tmp_id=" + data.tmp_id;

				if (data.verification.method == 'OTP App') {
					continue_otp_app(data.verification.setup, data.verification.qrcode);
				} else if (data.verification.method == 'SMS') {
					continue_sms(data.verification.setup, data.verification.prompt);
				} else if (data.verification.method == 'Email') {
					continue_email(data.verification.setup, data.verification.prompt);
				}
			}
		},
		401: get_error_handler({{ _("Invalid Login. Try again.") | tojson }}),
		417: get_error_handler({{ _("Oops! Something went wrong.") | tojson }}),
		429: get_error_handler({{ _("Too many requests. Please try again later.") | tojson }}),
		500: get_error_handler({{ _("Something went wrong.") | tojson }}),
	};

	return login_handlers;
})();

frappe.ready(function () {

	login.bind_events();
	if (window.show_footer_on_login) {
		$("body .web-footer").show();
	}

	$(".form-signup, .form-forgot, .form-login-with-email-link").removeClass("hide");
	$(document).trigger('login_rendered');
});

var verify_token = function (event) {
	$(".form-verify").on("submit", function (eventx) {
		eventx.preventDefault();
		var args = {};
		args.cmd = "login";
		args.otp = $("#login_token").val();
		args.tmp_id = frappe.get_cookie('tmp_id');
		if (!args.otp) {
			{# striptags is used to remove newlines, e is used for escaping #}
			frappe.msgprint("{{ _('Login token required') | striptags | e }}");
			return false;
		}
		login.call(args);
		return false;
	});
}

var request_otp = function (r) {
	$('.login-content').empty();
	$('.login-content:visible').append(
		`<div id="twofactor_div">
			<form class="form-verify">
				<div class="page-card-head p-0">
					<span class="indicator blue" data-text="Verification">{{ _("Verification") | e }}</span>
				</div>
				<div id="otp_div"></div>
				<input type="text" id="login_token" autocomplete="off" class="form-control" placeholder="{{ _("Verification Code") | e }}" required="">
				<button class="btn btn-sm btn-primary btn-block mt-3" id="verify_token">{{ _("Verify") | e }}</button>
			</form>
		</div>`
	);
	// add event handler for submit button
	verify_token();
	$("#login_token").get(0)?.focus();
}

var continue_otp_app = function (setup, qrcode) {
	request_otp();
	var qrcode_div = $('<div class="text-muted" style="padding-bottom: 15px;"></div>');

	if (setup) {
		direction = $('<div>').attr('id', 'qr_info').text({{ _("Enter Code displayed in OTP App.") | tojson }});
		qrcode_div.append(direction);
		$('#otp_div').prepend(qrcode_div);
	} else {
		direction = $('<div>').attr('id', 'qr_info').text({{ _("OTP setup using OTP App was not completed. Please contact Administrator.") | tojson }});
		qrcode_div.append(direction);
		$('#otp_div').prepend(qrcode_div);
	}
}

var continue_sms = function (setup, prompt) {
	request_otp();
	var sms_div = $('<div class="text-muted" style="padding-bottom: 15px;"></div>');

	if (setup) {
		sms_div.append(prompt)
		$('#otp_div').prepend(sms_div);
	} else {
		direction = $('<div>').attr('id', 'qr_info').html(prompt || {{ _("SMS was not sent. Please contact Administrator.") | tojson }});
		sms_div.append(direction);
		$('#otp_div').prepend(sms_div)
	}
}

var continue_email = function (setup, prompt) {
	request_otp();
	var email_div = $('<div class="text-muted" style="padding-bottom: 15px;"></div>');

	if (setup) {
		email_div.append(prompt)
		$('#otp_div').prepend(email_div);
	} else {
		var direction = $('<div>').attr('id', 'qr_info').html(prompt || {{ _("Verification code email not sent. Please contact Administrator.") | tojson }});
		email_div.append(direction);
		$('#otp_div').prepend(email_div);
	}
}

var mobile_login_state = {
	challenge_id: null,
	last_mobile: null,
	cooldown_timer: null,
	is_mobile_mode: false
};

var get_mobile_login_error_message = function (error) {
	var data = (error && error.responseJSON) || {};
	if (data._server_messages) {
		try {
			var server_messages = JSON.parse(data._server_messages || "[]");
			if (Array.isArray(server_messages) && server_messages.length) {
				var parsed = JSON.parse(server_messages[0]);
				return parsed.message || "درخواست با خطا مواجه شد.";
			}
		} catch (e) {
			return "درخواست با خطا مواجه شد.";
		}
	}
	return "درخواست با خطا مواجه شد.";
};

var normalize_mobile_login_input = function (value) {
	if (!value) return "";
	const persian_to_english = {
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
	};
	var output = "";
	for (const ch of String(value).trim()) {
		if (persian_to_english[ch]) {
			output += persian_to_english[ch];
		} else if (/[0-9+]/.test(ch)) {
			output += ch;
		}
	}
	return output;
}

var set_mobile_login_message = function (message, is_error) {
	var message_el = $("#mobile-login-message");
	message_el.text(message || "");
	message_el.css("color", is_error ? "#c53030" : "#1a7f37");
}

var set_mobile_login_send_cooldown = function (seconds) {
	var send_button = $("#mobile-login-send");
	var remaining = parseInt(seconds, 10) || 0;
	var default_label = "ارسال کد";

	if (mobile_login_state.cooldown_timer) {
		clearInterval(mobile_login_state.cooldown_timer);
		mobile_login_state.cooldown_timer = null;
	}

	if (remaining <= 0) {
		send_button.prop("disabled", false).text(default_label);
		return;
	}

	send_button.prop("disabled", true).text(default_label + " (" + remaining + "s)");
	mobile_login_state.cooldown_timer = setInterval(function () {
		remaining -= 1;
		if (remaining <= 0) {
			clearInterval(mobile_login_state.cooldown_timer);
			mobile_login_state.cooldown_timer = null;
			send_button.prop("disabled", false).text(default_label);
			return;
		}
		send_button.text(default_label + " (" + remaining + "s)");
	}, 1000);
}

var set_mobile_login_mode = function (enabled) {
	var email_group = $("#login_email").closest(".form-group");
	var password_group = $("#login_password").closest(".form-group");
	var forgot_password = $(".for-login .forgot-password-message").first();
	var login_button = $(".for-login .btn-login").first();
	var ldap_button = $(".for-login .btn-ldap-login").first();
	var toggle_button = $("#mobile-login-toggle");
	var sign_up_message = $(".for-login .sign-up-message").first();

	mobile_login_state.is_mobile_mode = enabled;
	set_mobile_login_message("", false);

	if (enabled) {
		email_group.hide();
		password_group.hide();
		forgot_password.hide();
		login_button.hide();
		ldap_button.hide();
		sign_up_message.hide();
		toggle_button.text("بازگشت به ورود با رمز");
		$("#mobile-login-panel").show();
		$("#mobile-login-number").focus();
		return;
	}

	email_group.show();
	password_group.show();
	forgot_password.show();
	login_button.show();
	ldap_button.show();
	sign_up_message.show();
	toggle_button.text("ورود با کد پیامکی");
	$("#mobile-login-panel").hide();
	$("#mobile-login-otp-step").hide();
	$("#mobile-login-otp").val("");
	mobile_login_state.challenge_id = null;
	set_mobile_login_send_cooldown(0);
	$("#login_email").focus();
}

var setup_mobile_login_events = function () {
	$("#mobile-login-toggle").on("click", function () {
		set_mobile_login_mode(!mobile_login_state.is_mobile_mode);
	});

	$("#mobile-login-back").on("click", function () {
		$("#mobile-login-otp-step").hide();
		$("#mobile-login-otp").val("");
		mobile_login_state.challenge_id = null;
		set_mobile_login_message("", false);
	});

	$("#mobile-login-send").on("click", function () {
		var mobile = normalize_mobile_login_input($("#mobile-login-number").val());
		if (!mobile) {
			set_mobile_login_message("لطفا شماره موبایل را وارد کنید.", true);
			return;
		}

		set_mobile_login_message("در حال ارسال کد تایید...", false);
		frappe.call({
			method: "frappe.mobile_login.send_mobile_login_otp",
			type: "POST",
			args: { mobile: mobile },
			freeze: true
		}).then(function (response) {
			var result = response && response.message || {};
			if (result.cooldown) {
				mobile_login_state.challenge_id = result.challenge_id || mobile_login_state.challenge_id;
				mobile_login_state.last_mobile = mobile;
				$("#mobile-login-otp-step").show();
				set_mobile_login_send_cooldown(result.retry_after || 60);
				set_mobile_login_message(
					result.message || "کد قبلا ارسال شده است. لطفا کمی صبر کنید.",
					false
				);
				$("#mobile-login-otp").focus();
				return;
			}

			mobile_login_state.challenge_id = result.challenge_id || null;
			mobile_login_state.last_mobile = mobile;
			$("#mobile-login-otp-step").show();
			set_mobile_login_send_cooldown(60);
			set_mobile_login_message("کد تایید ارسال شد. کد را وارد کنید.", false);
			$("#mobile-login-otp").focus();
		}).catch(function (error) {
			set_mobile_login_message(get_mobile_login_error_message(error), true);
		});
	});

	$("#mobile-login-verify").on("click", function () {
		var otp = ($("#mobile-login-otp").val() || "").trim();
		if (!otp) {
			set_mobile_login_message("کد تایید را وارد کنید.", true);
			return;
		}
		if (!mobile_login_state.challenge_id) {
			set_mobile_login_message("لطفا دوباره کد دریافت کنید.", true);
			return;
		}

		set_mobile_login_message("در حال بررسی کد...", false);
		frappe.call({
			method: "frappe.mobile_login.login_via_mobile_otp",
			type: "POST",
			args: {
				mobile: mobile_login_state.last_mobile || normalize_mobile_login_input($("#mobile-login-number").val()),
				otp: otp,
				challenge_id: mobile_login_state.challenge_id
			},
			freeze: true
		}).then(function (response) {
			var result = response && response.message || {};
			if (!result.logged_in) {
				set_mobile_login_message("ورود ناموفق بود.", true);
				return;
			}
			document.body.innerHTML = `{% include "templates/includes/splash_screen.html" %}`;
			window.location.href =
				frappe.utils.sanitise_redirect(frappe.utils.get_url_arg("redirect-to")) ||
				result.redirect_to ||
				result.home_page ||
				"/app";
		}).catch(function (error) {
			set_mobile_login_message(get_mobile_login_error_message(error), true);
		});
	});
}

var render_mobile_login = function () {
	if (window.location.pathname !== "/login") return;
	if ($("#mobile-login-toggle").length) return;

	document.documentElement.setAttribute("dir", "rtl");
	document.documentElement.setAttribute("lang", "fa");

	var actions = $(".for-login .form-login .page-card-actions").first();
	if (!actions.length) return;

	actions.append(
		`<div class="mt-2">
			<button type="button" class="btn btn-sm btn-default btn-block" id="mobile-login-toggle">ورود با کد پیامکی</button>
			<div id="mobile-login-panel" style="display:none; margin-top: 0.75rem; text-align: right;">
				<div class="form-group">
					<input type="text" id="mobile-login-number" class="form-control" placeholder="0912xxxxxxx" autocomplete="tel">
				</div>
				<button type="button" class="btn btn-sm btn-primary btn-block" id="mobile-login-send">ارسال کد</button>
				<div id="mobile-login-otp-step" style="display:none; margin-top: 0.75rem;">
					<div class="form-group">
						<input type="text" id="mobile-login-otp" class="form-control" placeholder="کد 6 رقمی" autocomplete="one-time-code">
					</div>
					<button type="button" class="btn btn-sm btn-primary btn-block" id="mobile-login-verify">ورود</button>
					<button type="button" class="btn btn-sm btn-default btn-block mt-2" id="mobile-login-back">دریافت کد جدید</button>
				</div>
				<div id="mobile-login-message" style="margin-top: 0.75rem; font-size: 12px;"></div>
			</div>
		</div>`
	);

	var login_email = ($("#login_email").val() || "").trim();
	if (/^(\+?98|0098|0)?9\d{9}$/.test(login_email)) {
		$("#mobile-login-number").val(login_email);
	}

	setup_mobile_login_events();
}

$(document).on("login_rendered", function () {
	render_mobile_login();
});

login.route();
