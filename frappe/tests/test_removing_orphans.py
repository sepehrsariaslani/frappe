import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.model.sync import remove_orphan_entities
from frappe.modules.export_file import delete_folder
from frappe.tests import IntegrationTestCase


class TestRemovingOrphanEntityIteration(unittest.TestCase):
	def test_walks_explicit_entity_list_without_database_access(self):
		fake_frappe = SimpleNamespace(
			get_all=Mock(return_value=[]),
			db=SimpleNamespace(commit=Mock()),
			delete_doc=Mock(),
		)
		with (
			patch("frappe.model.sync.create_entity_file_map", return_value={"Sidebar": {}}),
			patch("frappe.model.sync.frappe", fake_frappe),
		):
			remove_orphan_entities("Sidebar")

		fake_frappe.get_all.assert_called_once_with("Sidebar", filters={"standard": True}, fields=["name"])
		fake_frappe.db.commit.assert_called_once_with()


class TestRemovingOrphans(IntegrationTestCase):
	def test_removing_orphan(self):
		_before = frappe.conf.developer_mode
		frappe.conf.developer_mode = True
		# Create a new report
		report = frappe.new_doc("Report")
		args = {
			"doctype": "Report",
			"report_name": "Orphan Report",
			"ref_doctype": "DocType",
			"is_standard": "Yes",
			"module": "Custom",
		}
		report.update(args)
		report.save()
		print(f"Created report: {report.name}")
		# delete only fixture (emulating that the export/entity is deleted by the developer)
		delete_folder("Custom", "Report", report.name)
		self.assertTrue(frappe.db.exists("Report", report.name))
		if frappe.db.exists("Report", report.name):
			remove_orphan_entities()
		self.assertFalse(frappe.db.exists("Report", report.name))
		frappe.conf.developer_mode = _before
