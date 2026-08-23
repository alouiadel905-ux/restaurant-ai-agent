"""
Module responsable de la validation de données de contact,
notamment les numéros de téléphone. Cette validation est faite
en code Python pur, indépendamment de ce que l'IA a pu comprendre,
car on ne peut jamais garantir qu'un LLM applique une règle de
format à 100% du temps.
"""

import re


def validate_and_normalize_phone(phone: str | None) -> str | None:
    """
    Vérifie qu'un numéro de téléphone est un numéro français valide
    (10 chiffres), et le retourne normalisé (chiffres uniquement,
    commençant par 0). Retourne None si le numéro est invalide ou absent.

    Accepte plusieurs formats en entrée : "06 12 34 56 78",
    "0612345678", "+33612345678", "0033612345678".
    """
    if not phone:
        return None

    # On ne garde que les chiffres, en retirant espaces, points, tirets...
    digits = re.sub(r"\D", "", phone)

    # Gère les préfixes internationaux français (+33 ou 0033)
    if digits.startswith("33") and len(digits) == 11:
        digits = "0" + digits[2:]
    elif digits.startswith("0033") and len(digits) == 13:
        digits = "0" + digits[4:]

    # Un numéro français valide fait exactement 10 chiffres et
    # commence par 0 (ex: 0612345678).
    if len(digits) != 10 or not digits.startswith("0"):
        return None

    return digits


if __name__ == "__main__":
    # Quelques tests rapides pour vérifier le comportement
    test_cases = [
        "06 12 34 56 78",
        "0612345678",
        "+33612345678",
        "0978567578575",  # invalide : trop de chiffres
        "12345",          # invalide : trop court
        None,
    ]
    for case in test_cases:
        print(f"{case!r:30} -> {validate_and_normalize_phone(case)}")