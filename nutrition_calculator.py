"""
Nutrition Calculator for Finished Products based on BOM.
Skips non-food items (packaging) when calculating.
"""

import frappe
from frappe.utils import flt

# Items to skip in nutrition calculation (packaging, non-edible)
NON_FOOD_KEYWORDS = ["لیوان", "درب", "کاسه", "جعبه", "کاغذی", "کلمبیا", "اسموتی", "کن", "یخ", "آیس"]

def is_food_item(item_name):
    """Check if an item is food (not packaging)."""
    if not item_name:
        return False
    for kw in NON_FOOD_KEYWORDS:
        if kw in item_name:
            return False
    return True


def calculate_product_nutrition(item_code):
    """
    Calculate nutrition for a finished product based on its BOM components.
    Only includes food items (skips packaging).
    Nutrition values in DB are per 100g.
    """
    bom = frappe.get_all("BOM",
        filters={"item": item_code, "is_active": 1, "is_default": 1},
        fields=["name", "quantity"],
        limit_page_length=1
    )
    
    if not bom:
        bom = frappe.get_all("BOM",
            filters={"item": item_code, "is_active": 1},
            fields=["name", "quantity"],
            limit_page_length=1
        )
    
    if not bom:
        return None
    
    bom_name = bom[0]["name"]
    bom_qty = flt(bom[0]["quantity"]) or 1.0
    
    bom_items = frappe.get_all("BOM Item",
        filters={"parent": bom_name},
        fields=["item_code", "qty", "uom", "item_name"],
        limit_page_length=100
    )
    
    total_kcal = 0
    total_protein = 0
    total_fat = 0
    total_carb = 0
    total_sugar = 0
    
    for bi in bom_items:
        # Skip non-food items
        if not is_food_item(bi.get("item_name", "")):
            continue
        
        # Skip items with no nutrition data
        comp = frappe.get_all("Item",
            filters={"item_code": bi["item_code"]},
            fields=[
                "restaurant_nutrition_kcal",
                "restaurant_nutrition_protein_g",
                "restaurant_nutrition_fat_g",
                "restaurant_nutrition_carb_g",
                "restaurant_nutrition_sugar_g",
            ],
            limit_page_length=1
        )
        
        if not comp:
            continue
        
        c = comp[0]
        if not c.restaurant_nutrition_kcal:
            continue
        
        qty = flt(bi["qty"]) or 0
        uom = (bi.get("uom") or "").lower()
        
        # Convert to 100g equivalent
        if uom in ("گرم", "g", "gram"):
            factor = qty / 100.0
        elif uom in ("لیتر", "l", "liter"):
            factor = (qty * 1000) / 100.0
        elif uom in ("عدد", "piece"):
            factor = (qty * 50) / 100.0
        elif uom in ("اسلایس", "slice"):
            factor = (qty * 30) / 100.0
        else:
            factor = qty / 100.0
        
        total_kcal += flt(c.restaurant_nutrition_kcal) * factor
        total_protein += flt(c.restaurant_nutrition_protein_g) * factor
        total_fat += flt(c.restaurant_nutrition_fat_g) * factor
        total_carb += flt(c.restaurant_nutrition_carb_g) * factor
        total_sugar += flt(c.restaurant_nutrition_sugar_g) * factor
    
    # Per serving
    return {
        "kcal": round(total_kcal / bom_qty, 1),
        "protein_g": round(total_protein / bom_qty, 1),
        "fat_g": round(total_fat / bom_qty, 1),
        "carb_g": round(total_carb / bom_qty, 1),
        "sugar_g": round(total_sugar / bom_qty, 1),
    }


def update_product_nutrition(item_code):
    """Calculate and update nutrition on Item doc."""
    nutrition = calculate_product_nutrition(item_code)
    if not nutrition:
        return None
    
    item = frappe.get_doc("Item", item_code)
    item.restaurant_nutrition_kcal = nutrition["kcal"]
    item.restaurant_nutrition_protein_g = nutrition["protein_g"]
    item.restaurant_nutrition_fat_g = nutrition["fat_g"]
    item.restaurant_nutrition_carb_g = nutrition["carb_g"]
    item.restaurant_nutrition_sugar_g = nutrition["sugar_g"]
    item.save()
    return nutrition


def calculate_all_products_nutrition():
    """Calculate nutrition for ALL products with active BOMs."""
    boms = frappe.get_all("BOM",
        filters={"is_active": 1, "is_default": 1},
        fields=["item"],
        limit_page_length=200
    )
    
    results = {"updated": [], "skipped": [], "errors": []}
    
    for bom in boms:
        item_code = bom["item"]
        try:
            nutrition = update_product_nutrition(item_code)
            if nutrition and nutrition["kcal"] > 0:
                item = frappe.get_doc("Item", item_code)
                results["updated"].append({
                    "item": item.item_name,
                    "code": item_code,
                    "kcal": nutrition["kcal"],
                    "protein": nutrition["protein_g"],
                    "fat": nutrition["fat_g"],
                    "carb": nutrition["carb_g"],
                })
            else:
                results["skipped"].append(item_code)
        except Exception as e:
            results["errors"].append(item_code + ": " + str(e))
    
    return results


if __name__ == "__main__":
    import json
    results = calculate_all_products_nutrition()
    print(json.dumps(results, ensure_ascii=False, indent=2))
