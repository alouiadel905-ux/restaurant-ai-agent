"""
Module responsable de détecter, de façon simple et rapide (sans appel
IA), si un message du client ressemble à une confirmation.

Utilisé pour éviter d'appeler l'extraction de commande (qui consomme
un appel API) après CHAQUE message — seulement quand c'est probablement
utile, ce qui réduit fortement la consommation du quota Groq.
"""

CONFIRMATION_KEYWORDS = [
    "oui", "ouais", "ouai", "yes", "exact", "correct", "parfait",
    "valide", "valider", "confirme", "confirmer", "c'est bon",
    "c'est ça", "d'accord", "daccord", "ok", "okay", "nickel",
    "c'est tout", "ce sera tout", "j'ai terminé", "j'ai fini",
]


def looks_like_confirmation(text: str) -> bool:
    """
    Retourne True si le texte contient un mot ou une expression
    évoquant une confirmation. Volontairement simple (pas d'appel IA) :
    quelques faux positifs/négatifs sont acceptables, l'objectif est
    juste de limiter les appels d'extraction inutiles, pas d'être
    parfaitement précis (l'extraction elle-même reste la source de
    vérité pour le statut réel de la commande).
    """
    normalized = text.lower().strip()
    return any(keyword in normalized for keyword in CONFIRMATION_KEYWORDS)