"""
Module responsable de la transformation du menu (dictionnaire Python)
en un texte lisible, destiné à être inséré dans le prompt envoyé
au modèle IA (Groq).
"""

from src.menu.loader import load_menu


def _format_price(price: float) -> str:
    """Formate un prix avec 2 décimales et le symbole euro."""
    return f"{price:.2f}€"


def _format_item(item: dict) -> str:
    """
    Formate un seul item du menu en une ligne de texte lisible.
    Exemple : "- Margherita (Sauce Tomate, Mozzarella) : 7.50€"
    Ou avec tailles : "- Margherita (...) : Junior 7.50€ / Senior 16.00€ / Mega 19.00€"
    """
    name = item["name"]
    description = item.get("description")
    sizes = item.get("sizes")

    # Partie description entre parenthèses (si elle existe)
    desc_part = f" ({description})" if description else ""

    # Partie prix : soit un prix fixe, soit une liste de tailles
    if sizes:
        prices_text = " / ".join(
            f"{size['name']} {_format_price(size['price'])}"
            for size in sizes
        )
    else:
        prices_text = _format_price(item["price"])

    return f"- {name}{desc_part} : {prices_text}"


def _format_customization(customization: dict) -> str:
    """
    Formate les options de personnalisation d'une catégorie
    (utilisé pour les Tacos : viandes, extras, sauces).
    """
    lines = []

    if "meat_choices" in customization:
        meats = ", ".join(customization["meat_choices"])
        lines.append(f"  Viandes au choix : {meats}")

    if "extras" in customization:
        extras = ", ".join(
            f"{extra['name']} (+{_format_price(extra['price'])})"
            for extra in customization["extras"]
        )
        lines.append(f"  Extras disponibles : {extras}")

    if "sauces" in customization:
        sauces = ", ".join(customization["sauces"])
        lines.append(f"  Sauces au choix (gratuites) : {sauces}")

    return "\n".join(lines)


def format_menu_for_prompt(menu: dict) -> str:
    """
    Transforme le menu complet en un texte structuré, lisible
    par un humain ou un modèle IA. C'est ce texte qui sera inséré
    dans le prompt système envoyé à Groq.
    """
    lines = [f"MENU DU RESTAURANT {menu['restaurant']}", ""]

    for category in menu["categories"]:
        lines.append(f"=== {category['name'].upper()} ===")

        # Affiche la description de catégorie si elle existe
        # (ex: "Junior 26cm / Senior 33cm / Mega 40cm" pour les pizzas)
        if category.get("description"):
            lines.append(f"({category['description']})")

        # Affiche chaque item de la catégorie
        for item in category["items"]:
            lines.append(_format_item(item))

        # Affiche les options de personnalisation si elles existent
        if category.get("customization"):
            lines.append(_format_customization(category["customization"]))

        lines.append("")  # ligne vide entre les catégories

    return "\n".join(lines)


def format_menu_with_ids(menu: dict) -> str:
    """
    Variante de format_menu_for_prompt() qui inclut l'identifiant
    technique (id) de chaque item. Utilisée uniquement pour
    l'extraction de commande, afin que l'IA puisse répondre avec
    des identifiants exacts plutôt que des noms libres (qui peuvent
    se ressembler entre catégories, ex: "Chèvre Miel" existe en
    burger, en sandwich et en pizza).
    """
    lines = []

    for category in menu["categories"]:
        lines.append(f"=== {category['name'].upper()} ===")

        for item in category["items"]:
            price_info = _format_item(item)
            lines.append(f"[id: {item['id']}] {price_info}")

        lines.append("")

    return "\n".join(lines)


def build_vocabulary_hint(menu: dict) -> str:
    """
    Construit une liste courte de mots-clés du menu (noms de produits,
    viandes, sauces, extras), destinée à être donnée à Whisper comme
    "initial_prompt" pour orienter la reconnaissance vocale vers le
    vocabulaire attendu (ex: reconnaître "mayonnaise" plutôt qu'un
    mot proche sans rapport avec la restauration).
    """
    words = set()

    for category in menu["categories"]:
        for item in category["items"]:
            words.add(item["name"])

        customization = category.get("customization", {})
        for meat in customization.get("meat_choices", []):
            words.add(meat)
        for sauce in customization.get("sauces", []):
            words.add(sauce)
        for extra in customization.get("extras", []):
            words.add(extra["name"])

    return ", ".join(sorted(words))


if __name__ == "__main__":
    # Test rapide : génère le texte et l'affiche dans le terminal
    menu = load_menu()
    menu_text = format_menu_for_prompt(menu)
    print(menu_text)
    print("---")
    print(f"Longueur du texte généré : {len(menu_text)} caractères")