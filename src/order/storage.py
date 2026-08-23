"""
Module responsable de la sauvegarde persistante des commandes
confirmées. Utilise un fichier JSON comme stockage simple pour
ce prototype (migration possible vers une vraie base de données
plus tard, sans impacter le reste du code grâce à cette isolation).
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

# Fichier où toutes les commandes confirmées sont enregistrées.
ORDERS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "orders.json"


def _load_all_orders() -> list[dict]:
    """
    Charge la liste de toutes les commandes déjà sauvegardées.
    Retourne une liste vide si le fichier n'existe pas encore
    (cas du tout premier enregistrement).
    """
    if not ORDERS_PATH.exists():
        return []

    with open(ORDERS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_all_orders(orders: list[dict]) -> None:
    """Écrit la liste complète des commandes dans le fichier JSON."""
    with open(ORDERS_PATH, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)


def save_confirmed_order(verified_order: dict, customer_name: str | None = None,
                          customer_phone: str | None = None) -> dict:
    """
    Enregistre une commande vérifiée (voir calculator.py) de façon
    permanente. Ajoute un identifiant unique et un horodatage.

    Retourne la commande telle qu'enregistrée, avec ses métadonnées.
    """
    orders = _load_all_orders()

    order_record = {
        "order_id": str(uuid.uuid4())[:8],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "items": verified_order["items"],
        "total": verified_order["total"],
    }

    orders.append(order_record)
    _save_all_orders(orders)

    return order_record


if __name__ == "__main__":
    # Test rapide : sauvegarde une commande factice et vérifie
    # qu'elle est bien enregistrée.
    fake_order = {
        "items": [
            {"item_id": "tacos", "name": "Tacos", "quantity": 1, "line_total": 7.0}
        ],
        "total": 7.0,
    }
    saved = save_confirmed_order(fake_order, customer_name="Test", customer_phone="0600000000")
    print("Commande sauvegardée :")
    print(json.dumps(saved, indent=2, ensure_ascii=False))
    print(f"\nFichier : {ORDERS_PATH}")