import unittest
from importlib import import_module

import frappe


class TestMigrateHooks(unittest.TestCase):
	def test_frappe_after_migrate_hooks_resolve(self):
		for hook in frappe.get_hooks("after_migrate", app_name="frappe"):
			with self.subTest(hook=hook):
				module_name, function_name = hook.rsplit(".", 1)
				self.assertTrue(callable(getattr(import_module(module_name), function_name)))
