import frappe
import json

def run():
    def get_fields(doctype):
        meta = frappe.get_meta(doctype)
        # Get custom fields
        custom_fields = [df.fieldname for df in meta.fields if df.get('is_custom')]
        
        # Get discount/tax related standard fields if they are not custom
        important_standard = ['discount_amount', 'additional_discount_percentage', 'apply_discount_on', 'taxes_and_charges', 'shipping_address', 'company_address', 'base_grand_total', 'total_taxes_and_charges']
        
        # Get select/link fields for dropdowns
        link_fields = {df.fieldname: df.options for df in meta.fields if df.fieldtype in ['Link', 'Select']}
        
        return {
            "custom_fields": custom_fields,
            "important_standard": [f for f in important_standard if meta.get_field(f)],
            "link_fields": link_fields
        }

    print("---Quotation---")
    print(json.dumps(get_fields("Quotation"), indent=2))
    print("---Sales Order---")
    print(json.dumps(get_fields("Sales Order"), indent=2))
    print("---Sales Invoice---")
    print(json.dumps(get_fields("Sales Invoice"), indent=2))
