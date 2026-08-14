"""
Module responsable du chargement du menu du restaurant.

Ce module lit le fichier data/menu.json et expose des fonctions
pour accéder aux informations du menu (catégories, plats, prix).
"""

import json
from pathlib import Path

# Chemin vers le fichier menu.json, calculé de façon relative
# à ce fichier Python, pour que ça fonctionne peu importe
# depuis où le programme est lancé.
MENU_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "menu.json"


def load_menu() -> dict:
    """
    Charge le menu depuis le fichier JSON et le retourne
    sous forme de dictionnaire Python.
    """
    with open(MENU_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_all_items(menu: dict) -> list[dict]:
    """
    Retourne une liste plate de tous les items du menu,
    peu importe leur catégorie. Utile pour chercher un plat
    sans avoir à parcourir les catégories manuellement.
    """
    items = []
    for category in menu["categories"]:
        for item in category["items"]:
            items.append(item)
    return items


def find_item_by_id(menu: dict, item_id: str) -> dict | None:
    """
    Cherche un item du menu par son identifiant technique (id).
    Retourne None si aucun item ne correspond.
    """
    for item in get_all_items(menu):
        if item["id"] == item_id:
            return item
    return None


if __name__ == "__main__":
    # Ce bloc ne s'exécute que si on lance CE fichier directement
    # (utile pour tester rapidement le module de façon isolée).
    menu = load_menu()
    print(f"Restaurant : {menu['restaurant']}")
    print(f"Nombre de catégories : {len(menu['categories'])}")
    print(f"Nombre total d'items : {len(get_all_items(menu))}")

    test_item = find_item_by_id(menu, "pizza_margherita")
    print(f"Test recherche par id : {test_item}")