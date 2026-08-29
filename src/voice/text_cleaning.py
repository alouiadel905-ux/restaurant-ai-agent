"""
Module responsable du nettoyage du texte avant synthèse vocale.

Le texte généré par l'IA peut contenir du Markdown (gras, listes,
titres...) adapté à un affichage écrit, mais qu'un moteur de synthèse
vocale lirait littéralement (ex: "astérisque astérisque tacos"). Ce
module retire ce formatage pour ne garder que du texte naturel,
adapté à être lu à voix haute.
"""

import re


def strip_leaked_reasoning(text: str) -> str:
    """
    Filet de sécurité : détecte et retire les fragments de
    "raisonnement interne" du modèle qui auraient échappé au réglage
    reasoning_format="hidden" de l'API (ex: "User says: ... Need to
    ask again."). Ce texte ne doit jamais être vu ni entendu par le
    client.
    """
    # Motifs typiques de raisonnement qui fuite, souvent en anglais,
    # commençant par des tournures d'analyse interne.
    leak_patterns = [
        r"User says:.*?(?=\n|$)",
        r"The user (says|wants|is asking).*?(?=\n|$)",
        r"I (need|should|must) (to )?(ask|respond|say).*?(?=\n|\.)",
        r"This is (still )?not (a )?valid.*?(?=\n|\.)",
        r"Let me.*?(?=\n|\.)",
    ]

    cleaned = text
    for pattern in leak_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip()


def strip_markdown_for_speech(text: str) -> str:
    """
    Retire les symboles de mise en forme Markdown ET les éventuelles
    fuites de raisonnement interne d'un texte, pour le rendre adapté
    à la lecture à voix haute.
    """
    text = strip_leaked_reasoning(text)

    # Gras/italique : **texte** ou *texte* -> texte
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)

    # Puces de liste en début de ligne ("- élément" -> "élément")
    text = re.sub(r"^[\-\*]\s+", "", text, flags=re.MULTILINE)

    # Titres Markdown ("### Titre" -> "Titre")
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

    # Tableaux Markdown (lignes contenant plusieurs "|") : on retire
    # les barres verticales, qui n'ont aucun sens à l'oral.
    text = text.replace("|", " ")

    # Nettoyage des espaces multiples laissés par les remplacements
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()


if __name__ == "__main__":
    example = "Voici votre commande :\n- **Tacos L** : 8,00€\n- *Coca* : 1,50€\n\n**Total** : 9,50€"
    print("Avant :")
    print(example)
    print("\nAprès :")
    print(strip_markdown_for_speech(example))