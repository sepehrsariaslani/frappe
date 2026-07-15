import frappe
import json

def main():
    items = frappe.db.sql("SELECT name, description, item_group, restaurant_nutrition_kcal FROM `tabItem` WHERE restaurant_enabled = 1 ORDER BY item_group, `name`", as_dict=True)
    
    results = []
    for item in items:
        bom_items = frappe.db.sql("SELECT bi.item_code, bi.qty, bi.uom, i.item_name FROM `tabBOM Item` bi LEFT JOIN `tabItem` i ON i.name = bi.item_code WHERE bi.parent = %s", (item['name'],), as_dict=True)
        
        materials = []
        for bi in bom_items:
            name = bi.get('item_name') or bi['item_code']
            materials.append(name + " (" + str(bi['qty']) + " " + str(bi['uom']) + ")")
        
        desc = item.get('description') or ''
        has_html = '<p>' in desc
        is_ingredients_only = 'INGREDIENTS ONLY' in desc
        
        results.append(item['name'] + "|||" + item.get('item_group','') + "|||" + str(item.get('restaurant_nutrition_kcal',0)) + "|||" + str(has_html) + "|||" + str(is_ingredients_only) + "|||" + desc[:150] + "|||" + "|".join(materials[:10]))
    
    for r in results:
        print(r)

main()
