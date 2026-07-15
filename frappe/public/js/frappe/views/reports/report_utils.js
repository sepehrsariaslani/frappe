frappe.provide("frappe.report_utils");

frappe.report_utils = {
	make_chart_options: function (
		columns,
		raw_data,
		{ y_fields, x_field, chart_type, colors, height }
	) {
		const type = chart_type.toLowerCase();

		let rows = raw_data.result.filter((value) => Object.keys(value).length);

		let labels = get_column_values(x_field);
		let datasets = y_fields.map((y_field) => ({
			name: get_translated_column_label(y_field),
			values: get_column_values(y_field).map((d) => Number(d)),
		}));

		if (raw_data.add_total_row) {
			labels = labels.slice(0, -1);
			datasets.forEach((dataset) => {
				dataset.values = dataset.values.slice(0, -1);
			});
		}

		return {
			data: {
				labels: labels.length ? labels : null,
				datasets: datasets,
			},
			truncateLegends: 1,
			type: type,
			height: height ? height : 280,
			colors: colors,
			axisOptions: {
				shortenYAxisNumbers: 1,
				xAxisMode: "tick",
				numberFormatter: frappe.utils.format_chart_axis_number,
			},
		};

		function get_column_values(column_name) {
			if (Array.isArray(rows[0])) {
				let column_index = columns.findIndex((column) => column.fieldname == column_name);
				return rows.map((row) => row[column_index]);
			} else {
				return rows.map((row) => row[column_name]);
			}
		}

		function get_translated_column_label(fieldname) {
			let column = columns.find((column) => column.fieldname === fieldname);
			return column?.label ?? __(frappe.model.unscrub(fieldname));
		}
	},

	get_field_options_from_report: function (columns, data) {
		const rows = data.result.filter((value) => Object.keys(value).length);
		const first_row = Array.isArray(rows[0])
			? rows[0]
			: columns.map((col) => rows[0][col.fieldname]);

		const indices = first_row.reduce((accumulator, current_value, current_index) => {
			if (Number.isFinite(current_value)) {
				accumulator.push(current_index);
			}
			return accumulator;
		}, []);

		function get_options(fields) {
			return fields.map((field) => {
				if (field.fieldname) {
					return { label: field.label, value: field.fieldname };
				} else {
					field = frappe.report_utils.prepare_field_from_column(field);
					return { label: field.label, value: field.fieldname };
				}
			});
		}

		const numeric_fields = columns.filter((col, i) => indices.includes(i));
		const non_numeric_fields = columns.filter((col, i) => !indices.includes(i));

		let numeric_field_options = get_options(numeric_fields);
		let non_numeric_field_options = get_options(non_numeric_fields);

		return {
			numeric_fields: numeric_field_options,
			non_numeric_fields: non_numeric_field_options,
		};
	},

	prepare_field_from_column: function (column) {
		if (typeof column === "string") {
			if (column.includes(":")) {
				let [label, fieldtype, width] = column.split(":");
				let options;

				if (fieldtype.includes("/")) {
					[fieldtype, options] = fieldtype.split("/");
				}

				column = {
					label,
					fieldname: label,
					fieldtype,
					width,
					options,
				};
			} else {
				column = {
					label: column,
					fieldname: column,
					fieldtype: "Data",
				};
			}
		}
		return column;
	},

	get_report_filters: function (report_name) {
		if (frappe.query_reports[report_name]) {
			let filters = frappe.query_reports[report_name].filters;
			return Promise.resolve(filters);
		}

		return frappe
			.xcall("frappe.desk.query_report.get_script", {
				report_name: report_name,
			})
			.then((r) => {
				frappe.dom.eval(r.script);
				return frappe.after_ajax(() => {
					if (
						frappe.query_reports[report_name] &&
						!frappe.query_reports[report_name].filters &&
						r.filters
					) {
						return (frappe.query_reports[report_name].filters = r.filters);
					}
					return (
						frappe.query_reports[report_name] &&
						frappe.query_reports[report_name].filters
					);
				});
			});
	},

	get_filter_values(filters) {
		return filters
			.map((f) => {
				var v = f.default;
				return {
					[f.fieldname]: v,
				};
			})
			.reduce((acc, f) => {
				Object.assign(acc, f);
				return acc;
			}, {});
	},

	get_result_of_fn(fn, values) {
		const get_result = {
			Minimum: (values) => values.reduce((min, val) => Math.min(min, val), values[0]),
			Maximum: (values) => values.reduce((min, val) => Math.max(min, val), values[0]),
			Average: (values) => values.reduce((a, b) => a + b, 0) / values.length,
			Sum: (values) => values.reduce((a, b) => a + b, 0),
		};
		return get_result[fn](values);
	},

	get_export_dialog(report_name, extra_fields, callback) {
		const fields = [
			{
				label: "File Format",
				fieldname: "file_format",
				fieldtype: "Select",
				options: ["Excel", "CSV"],
				default: "Excel",
				reqd: 1,
			},
			{
				label: __("Export in Background"),
				fieldname: "export_in_background",
				fieldtype: "Check",
			},
			{
				fieldtype: "Section Break",
				fieldname: "csv_settings",
				label: "Settings",
				collapsible: 1,
				depends_on: "eval:doc.file_format=='CSV'",
			},
			{
				fieldtype: "Data",
				label: "CSV Delimiter",
				fieldname: "csv_delimiter",
				default: ",",
				length: 1,
				depends_on: "eval:doc.file_format=='CSV'",
			},
			{
				fieldtype: "Select",
				label: "CSV Quoting",
				fieldname: "csv_quoting",
				options: [
					{ value: 0, label: "Minimal" },
					{ value: 1, label: "All" },
					{ value: 2, label: "Non-numeric" },
					{ value: 3, label: "None" },
				],
				default: 2,
				depends_on: "eval:doc.file_format=='CSV'",
			},
			{
				fieldtype: "Data",
				label: "CSV Decimal Separator",
				fieldname: "csv_decimal_sep",
				default: ".",
				length: 1,
				depends_on: "eval:doc.file_format=='CSV' && doc.csv_quoting != 2",
			},
			{
				fieldtype: "Small Text",
				label: "CSV Preview",
				fieldname: "csv_preview",
				read_only: 1,
				depends_on: "eval:doc.file_format=='CSV'",
			},
		];

		if (extra_fields) {
			fields.push(
				{
					fieldtype: "Section Break",
					fieldname: "extra_fields",
					collapsible: 0,
				},
				...extra_fields
			);
		}

		const dialog = new frappe.ui.Dialog({
			title: __("Export Report: {0}", [report_name], "Export report"),
			fields: fields,
			primary_action_label: __("Download", null, "Export report"),
			primary_action: callback,
		});

		function update_csv_preview(dialog) {
			const is_query_report = frappe.get_route()[0] === "query-report";
			const report = is_query_report ? frappe.query_report : cur_list;
			const columns = report.columns.filter((col) => col.hidden !== 1);
			let PREVIEW_DATA = [
				columns.map((col) => __(is_query_report ? col.label : col.name)),
				...report.data
					.slice(0, 3)
					.map((row) =>
						columns.map((col) => row[is_query_report ? col.fieldname : col.field])
					),
			];

			dialog.set_value(
				"csv_preview",
				frappe.report_utils.get_csv_preview(
					PREVIEW_DATA,
					dialog.get_value("csv_quoting"),
					dialog.get_value("csv_delimiter"),
					dialog.get_value("csv_decimal_sep")
				)
			);
		}

		dialog.fields_dict["file_format"].df.onchange = () => update_csv_preview(dialog);
		dialog.fields_dict["csv_quoting"].df.onchange = () => update_csv_preview(dialog);
		dialog.fields_dict["csv_delimiter"].df.onchange = () => {
			if (!dialog.get_value("csv_delimiter")) {
				dialog.set_value("csv_delimiter", ",");
			}
			update_csv_preview(dialog);
		};
		dialog.fields_dict["csv_decimal_sep"].df.onchange = () => {
			if (!dialog.get_value("csv_decimal_sep")) {
				dialog.set_value("csv_decimal_sep", ".");
			}
			update_csv_preview(dialog);
		};

		return dialog;
	},

	get_freeze_storage_key(report_name) {
		return `report_freeze_cols::${frappe.session.user}::${report_name || frappe.get_route_str()}`;
	},

	get_column_index(column, columns = []) {
		if (typeof column?.colIndex === "number") return column.colIndex;
		if (typeof column?.index === "number") return column.index;
		return columns.findIndex((col) => col.id === column?.id);
	},

	get_freeze_direction(datatable) {
		const direction =
			datatable?.options?.direction ||
			datatable?.datatableWrapper?.getAttribute?.("dir") ||
			(frappe.utils.is_rtl() ? "rtl" : "ltr");
		return direction === "rtl" ? "rtl" : "ltr";
	},

	can_apply_freeze_styles(datatable) {
		return Boolean(
			datatable?.getColumns &&
				datatable?.style?.setStyle &&
				datatable?.style?.styleEl &&
				datatable.style.styleEl.sheet &&
				datatable?.datatableWrapper?.isConnected !== false
		);
	},

	apply_zebra_rows(datatable, freeze_count = 0) {
		if (!this.can_apply_freeze_styles(datatable)) return;

		datatable.style.setStyle(".dt-scrollable .dt-row:nth-child(even) .dt-cell", {
			backgroundColor: "var(--subtle-fg, #f7f9fc)",
		});

		for (let col = 0; col < freeze_count; col++) {
			datatable.style.setStyle(`.dt-scrollable .dt-row:nth-child(even) .dt-cell--col-${col}`, {
				backgroundColor: "var(--dt-cell-bg, #fff)",
			});
		}
	},

	clear_frozen_columns(datatable) {
		if (!datatable?.getColumns) return;
		const columns = datatable.getColumns() || [];

		if (this.can_apply_freeze_styles(datatable)) {
			for (let col = 0; col < columns.length; col++) {
				datatable.style.setStyle(`.dt-scrollable .dt-cell--col-${col}`, {
					position: "",
					left: "",
					right: "",
					zIndex: "",
					backgroundColor: "",
					boxShadow: "",
				});
				datatable.style.setStyle(`.dt-header .dt-row-header .dt-cell--col-${col}`, {
					position: "",
					left: "",
					right: "",
					zIndex: "",
					backgroundColor: "",
					boxShadow: "",
				});
				datatable.style.setStyle(`.dt-header .dt-row-filter .dt-cell--col-${col}`, {
					position: "",
					left: "",
					right: "",
					zIndex: "",
					backgroundColor: "",
					boxShadow: "",
				});
			}
		}

		if (datatable.__freeze_reapply_scroll) {
			datatable.bodyScrollable?.removeEventListener("scroll", datatable.__freeze_reapply_scroll);
			datatable.__freeze_reapply_scroll = null;
		}

		if (datatable.__freeze_reapply_resize) {
			window.removeEventListener("resize", datatable.__freeze_reapply_resize);
			datatable.__freeze_reapply_resize = null;
		}

		if (datatable.__freeze_reapply_timer) {
			clearTimeout(datatable.__freeze_reapply_timer);
			datatable.__freeze_reapply_timer = null;
		}

		if (datatable.__freeze_retry_timer) {
			clearTimeout(datatable.__freeze_retry_timer);
			datatable.__freeze_retry_timer = null;
		}
	},

	apply_frozen_columns(datatable, freeze_count = 0, report_name = null) {
		if (!datatable?.getColumns) return;

		const freeze_key = this.get_freeze_storage_key(report_name);

		if (!this.can_apply_freeze_styles(datatable)) {
			clearTimeout(datatable.__freeze_retry_timer);
			datatable.__freeze_retry_timer = setTimeout(() => {
				if (this.can_apply_freeze_styles(datatable)) {
					this.apply_frozen_columns(datatable, freeze_count, report_name);
				}
			}, 60);
			return;
		}

		const columns = datatable.getColumns() || [];
		const direction = this.get_freeze_direction(datatable);
		const side = direction === "rtl" ? "right" : "left";
		const opposite_side = direction === "rtl" ? "left" : "right";

		this.clear_frozen_columns(datatable);
		freeze_count = Math.max(0, cint(freeze_count));

		if (!freeze_count) {
			this.apply_zebra_rows(datatable, 0);
			if (datatable.setDimensions) {
				setTimeout(() => datatable.setDimensions(), 0);
			}
			return;
		}

		let offset = 0;
		for (let col = 0; col < freeze_count && col < columns.length; col++) {
			const header_cell = datatable.header?.querySelector?.(`.dt-row-header .dt-cell--col-${col}`);
			const width = parseInt(
				header_cell?.offsetWidth || columns[col]?.width || columns[col]?._width || 180,
				10
			);

			const body_rule = {
				position: "sticky",
				zIndex: 20,
				backgroundColor: "var(--dt-cell-bg, #fff)",
				boxShadow: col === freeze_count - 1 ? "2px 0 0 rgba(0, 0, 0, 0.06)" : "",
			};
			body_rule[side] = `${offset}px`;
			body_rule[opposite_side] = "auto";

			const header_rule = {
				position: "sticky",
				zIndex: 30,
				backgroundColor: "var(--dt-header-cell-bg, #fff)",
				boxShadow: col === freeze_count - 1 ? "2px 0 0 rgba(0, 0, 0, 0.08)" : "",
			};
			header_rule[side] = `${offset}px`;
			header_rule[opposite_side] = "auto";

			const filter_rule = {
				position: "sticky",
				zIndex: 25,
				backgroundColor: "var(--dt-cell-bg, #fff)",
				boxShadow: col === freeze_count - 1 ? "2px 0 0 rgba(0, 0, 0, 0.06)" : "",
			};
			filter_rule[side] = `${offset}px`;
			filter_rule[opposite_side] = "auto";

			datatable.style.setStyle(`.dt-scrollable .dt-cell--col-${col}`, body_rule);
			datatable.style.setStyle(`.dt-header .dt-row-header .dt-cell--col-${col}`, header_rule);
			datatable.style.setStyle(`.dt-header .dt-row-filter .dt-cell--col-${col}`, filter_rule);

			offset += width;
		}

		datatable.style.setStyle(".dt-header .dt-row-filter .dt-cell", {
			backgroundColor: "var(--dt-cell-bg, #fff)",
			zIndex: 10,
		});
		datatable.style.setStyle(".dt-header", {
			position: "relative",
			zIndex: 15,
			backgroundColor: "var(--dt-header-bg, #fff)",
		});
		datatable.style.setStyle(".dt-header .dt-row", {
			position: "relative",
			zIndex: 16,
		});
		datatable.style.setStyle(".dt-header .dt-row-header .dt-cell", {
			backgroundColor: "var(--dt-header-cell-bg, #fff)",
		});
		datatable.style.setStyle(".dt-header .dt-dropdown", {
			zIndex: 1002,
		});
		datatable.style.setStyle(".dt-scrollable", {
			position: "relative",
			zIndex: 1,
		});

		datatable.style.setStyle(".dt-dropdown-container", { zIndex: 1000 });
		datatable.style.setStyle(".dt-dropdown__list", { zIndex: 1001 });

		if (datatable.setDimensions) {
			setTimeout(() => datatable.setDimensions(), 0);
		}
		this.apply_zebra_rows(datatable, freeze_count);

			const reapply = () => {
				clearTimeout(datatable.__freeze_reapply_timer);
				datatable.__freeze_reapply_timer = setTimeout(() => {
					if (!this.can_apply_freeze_styles(datatable)) return;
					const saved = parseInt(localStorage.getItem(freeze_key) || String(freeze_count), 10);
					this.apply_frozen_columns(datatable, saved, report_name);
				}, 80);
			};

		const on_scroll = () => {
			if (datatable.__freeze_scroll_tick) return;
			datatable.__freeze_scroll_tick = true;
			requestAnimationFrame(() => {
				datatable.__freeze_scroll_tick = false;
			});
		};

		datatable.__freeze_reapply_resize = reapply;
		datatable.__freeze_reapply_scroll = on_scroll;

		window.addEventListener("resize", reapply);
		datatable.bodyScrollable?.addEventListener("scroll", on_scroll, { passive: true });
	},

	apply_saved_frozen_columns(datatable, report_name) {
		const freeze_key = this.get_freeze_storage_key(report_name);
		const saved = parseInt(localStorage.getItem(freeze_key) || "0", 10);
		this.apply_frozen_columns(datatable, saved > 0 ? saved : 0, report_name);
	},

	extend_datatable_options_with_freeze(datatable_options, { report_name, get_datatable }) {
		const report_utils = frappe.report_utils;
		const freeze_key = report_utils.get_freeze_storage_key(report_name);
		const header_dropdown = datatable_options.headerDropdown || [];

		if (header_dropdown.some((item) => item?.__freeze_action)) {
			return datatable_options;
		}

		const freeze_actions = [
			{
				label: __("📌 فریز تا این ستون"),
				__freeze_action: true,
				action(column) {
					const datatable = get_datatable ? get_datatable() : null;
					if (!datatable) return;

					const columns = datatable.getColumns ? datatable.getColumns() || [] : [];
					const col_index = report_utils.get_column_index(column, columns);
					if (col_index < 0) return;

					const freeze_count = col_index + 1;
					localStorage.setItem(freeze_key, String(freeze_count));
					report_utils.apply_frozen_columns(datatable, freeze_count, report_name);
					frappe.show_alert({
						message: __("ستون‌ها فریز شدند"),
						indicator: "green",
					});
				},
			},
			{
				label: __("🧹 حذف فریز"),
				__freeze_action: true,
				action() {
					const datatable = get_datatable ? get_datatable() : null;
					if (!datatable) return;

					localStorage.removeItem(freeze_key);
					report_utils.apply_frozen_columns(datatable, 0, report_name);
					frappe.show_alert({
						message: __("فریز حذف شد"),
						indicator: "blue",
					});
				},
			},
		];

		datatable_options.headerDropdown = [...header_dropdown, ...freeze_actions];
		return datatable_options;
	},

	get_csv_preview(data, quoting, delimiter, decimal_sep) {
		// data: array of arrays
		// quoting: 0 - minimal, 1 - all, 2 - non-numeric, 3 - none
		// delimiter: any single character
		quoting = cint(quoting);
		const QUOTING = {
			Minimal: 0,
			All: 1,
			NonNumeric: 2,
			None: 3,
		};

		if (delimiter.length > 1) {
			frappe.throw(__("Delimiter must be a single character"));
		}

		if (decimal_sep.length > 1) {
			frappe.throw(__("Decimal Separator must be a single character"));
		}

		if (0 > quoting || quoting > 3) {
			frappe.throw(__("Quoting must be between 0 and 3"));
		}

		if (decimal_sep !== "." && quoting === QUOTING.NonNumeric) {
			frappe.throw(__("Decimal Separator must be '.' when Quoting is set to Non-numeric"));
		}

		return data
			.map((row) => {
				return row
					.map((col) => {
						if (col === null) {
							return "";
						}

						if (typeof col == "string" && col.includes('"')) {
							col = col.replace(/"/g, '""');
						}

						if (typeof col == "number" && decimal_sep !== ".") {
							col = col.toString().replace(".", decimal_sep);
						}

						switch (quoting) {
							case QUOTING.Minimal:
								return typeof col === "string" && col.includes(delimiter)
									? `"${col}"`
									: `${col}`;
							case QUOTING.All:
								return `"${col}"`;
							case QUOTING.NonNumeric:
								return isNaN(col) ? `"${col}"` : `${col}`;
							case QUOTING.None:
								return `${col}`;
						}
					})
					.join(delimiter);
			})
			.join("\n");
	},
};
