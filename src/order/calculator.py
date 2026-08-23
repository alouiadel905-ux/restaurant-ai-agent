"""
Module responsable du calcul FIABLE du montant d'une commande.

Contrairement au prix affiché par l'IA dans la conversation (utile
pour l'humain, mais pas garanti à 100%), ce module recalcule chaque
prix en allant chercher la vérité dans menu.json. C'est cette version
qui doit être utilisée pour toute décision financière réelle.
"""

from src.menu.loader import find_item_by_id


def _find_category_for_item(menu: dict, item_id: str) -> dict | None:
    """
    Retrouve la catégorie du menu à laquelle appartient un item
    donné (nécessaire pour accéder à ses options de personnalisation,
    comme les extras des tacos).
    """
    for category in menu["categories"]:
        for item in category["items"]:
            if item["id"] == item_id:
                return category
    return None


def _resolve_unit_price(base_item: dict, requested_size: str | None, warnings: list[str]) -> float:
    """
    Détermine le prix unitaire réel d'un item, à partir du menu,
    en tenant compte de la taille demandée si applicable.
    """
    sizes = base_item.get("sizes")

    if not sizes:
        return base_item["price"]

    if requested_size:
        for size in sizes:
            if size["name"].strip().lower() == requested_size.strip().lower():
                return size["price"]
        warnings.append(
            f"Taille '{requested_size}' non reconnue pour '{base_item['name']}', "
            f"prix le plus bas utilisé par défaut."
        )

    # Si aucune taille n'est précisée ou reconnue, on prend la plus
    # petite par sécurité (on ne veut jamais surfacturer par erreur).
    return min(size["price"] for size in sizes)


def _resolve_extras_total(category: dict | None, extras: list[str], warnings: list[str]) -> float:
    """
    Calcule le supplément total des extras demandés, en les
    comparant à la liste officielle des extras de la catégorie
    (ex: extras des tacos à +1.50€ chacun).

    Gère aussi le cas particulier de l'option "Gratiné" (+2.00€),
    qui est une catégorie séparée du menu, pas un extra classique.
    """
    total = 0.0
    known_extras = []

    if category and category.get("customization", {}).get("extras"):
        known_extras = category["customization"]["extras"]

    for extra_name in extras:
        normalized = extra_name.strip().lower()

        # Cas particulier : l'option "Gratiné" n'est pas un extra
        # classique, c'est un supplément fixe de +2.00€.
        if "gratin" in normalized:
            total += 2.00
            continue

        matched = next(
            (e for e in known_extras if e["name"].strip().lower() == normalized),
            None
        )

        if matched:
            total += matched["price"]
        else:
            warnings.append(f"Extra '{extra_name}' non reconnu dans le menu, ignoré du calcul.")

    return total


def calculate_order_total(order: dict, menu: dict) -> dict:
    """
    Recalcule intégralement une commande extraite (voir order_extractor.py)
    en utilisant les vrais prix du menu, et retourne une version
    "vérifiée" de la commande avec le montant total fiable.

    Ajoute une liste d'avertissements (warnings) si des incohérences
    ont été détectées (produit inconnu, taille inconnue, extra inconnu).
    """
    verified_items = []
    warnings: list[str] = []
    total = 0.0

    for order_item in order.get("items", []):
        item_id = order_item.get("item_id")
        base_item = find_item_by_id(menu, item_id)

        if base_item is None:
            warnings.append(f"Produit inconnu ignoré du calcul : '{item_id}'")
            continue

        category = _find_category_for_item(menu, item_id)
        quantity = order_item.get("quantity", 1)

        unit_price = _resolve_unit_price(base_item, order_item.get("size"), warnings)
        extras_total = _resolve_extras_total(category, order_item.get("extras", []), warnings)

        line_total = (unit_price + extras_total) * quantity
        total += line_total

        verified_items.append({
            "item_id": item_id,
            "name": base_item["name"],
            "quantity": quantity,
            "size": order_item.get("size"),
            "meats": order_item.get("meats", []),
            "extras": order_item.get("extras", []),
            "sauces": order_item.get("sauces", []),
            "unit_price": round(unit_price, 2),
            "extras_total": round(extras_total, 2),
            "line_total": round(line_total, 2),
        })

    return {
        "items": verified_items,
        "total": round(total, 2),
        "status": order.get("status", "in_progress"),
        "warnings": warnings,
    }