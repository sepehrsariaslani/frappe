import frappe

def run():
    # STEP 1: Rename items
    try:
        frappe.rename_doc("Item", "لیموناد", "لیموناد کوبایی")
        print("Renamed: لیموناد -> لیموناد کوبایی")
    except Exception as e:
        print(f"Rename لیموناد: {e}")
    
    try:
        frappe.rename_doc("Item", "موهیتو", "موهیتو کوبایی")
        print("Renamed: موهیتو -> موهیتو کوبایی")
    except Exception as e:
        print(f"Rename موهیتو: {e}")

    # STEP 2: Create new items
    for item_name in ["لیموناد توت فرنگی", "موهیتو توت فرنگی"]:
        existing = frappe.get_all("Item", filters={"item_name": item_name}, limit_page_length=1)
        if not existing:
            doc = frappe.get_doc({
                "doctype": "Item",
                "item_name": item_name,
                "item_group": "بار سرد",
                "stock_uom": "عدد",
                "is_stock_item": 0,
                "is_sales_item": 1,
            })
            doc.insert()
            print(f"Created item: {doc.item_name} ({doc.name})")
        else:
            print(f"Already exists: {item_name}")

    def get_code(name):
        items = frappe.get_all("Item", filters={"item_name": name}, fields=["item_code"], limit_page_length=1)
        return items[0].item_code if items else None

    # STEP 3: Create BOMs
    boms_data = [
        {
            "item": "لیموناد کوبایی",
            "qty": 1,
            "components": [
                ("لیمو ترش", 30, "گرم"),
                ("شکر", 15, "گرم"),
                ("آب گازدار", 0.15, "لیتر"),
                ("یخ", 50, "گرم"),
                ("لیوان کن", 1, "عدد"),
            ]
        },
        {
            "item": "موهیتو کوبایی",
            "qty": 1,
            "components": [
                ("لیمو ترش", 25, "گرم"),
                ("نعنا", 8, "گرم"),
                ("شکر", 20, "گرم"),
                ("آب گازدار", 0.15, "لیتر"),
                ("یخ", 60, "گرم"),
                ("لیوان کن", 1, "عدد"),
            ]
        },
        {
            "item": "لیموناد توت فرنگی",
            "qty": 1,
            "components": [
                ("لیمو ترش", 20, "گرم"),
                ("توت فرنگی", 80, "گرم"),
                ("شکر", 15, "گرم"),
                ("آب گازدار", 0.12, "لیتر"),
                ("یخ", 50, "گرم"),
                ("لیوان کن", 1, "عدد"),
            ]
        },
        {
            "item": "موهیتو توت فرنگی",
            "qty": 1,
            "components": [
                ("لیمو ترش", 20, "گرم"),
                ("نعنا", 6, "گرم"),
                ("توت فرنگی", 60, "گرم"),
                ("شکر", 15, "گرم"),
                ("آب گازدار", 0.12, "لیتر"),
                ("یخ", 60, "گرم"),
                ("لیوان کن", 1, "عدد"),
            ]
        },
    ]

    for bom_data in boms_data:
        item_code = get_code(bom_data["item"])
        if not item_code:
            print(f"ERROR: Item not found: {bom_data['item']}")
            continue
        
        existing_boms = frappe.get_all("BOM", filters={"item": item_code, "is_active": 1}, limit_page_length=1)
        if existing_boms:
            print(f"BOM already exists for {bom_data['item']}: {existing_boms[0].name}")
            continue
        
        bom_items = []
        for comp_name, comp_qty, comp_uom in bom_data["components"]:
            comp_code = get_code(comp_name)
            if not comp_code:
                print(f"  WARNING: Component not found: {comp_name}")
                continue
            bom_items.append({
                "item_code": comp_code,
                "qty": comp_qty,
                "uom": comp_uom,
            })
        
        bom_doc = frappe.get_doc({
            "doctype": "BOM",
            "item": item_code,
            "quantity": bom_data["qty"],
            "is_active": 1,
            "is_default": 1,
            "items": bom_items,
        })
        bom_doc.insert()
        bom_doc.submit()
        print(f"Created BOM: {bom_doc.name} for {bom_data['item']}")

    print("=== DONE ===")
    return "OK"
