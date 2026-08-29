"""
Module responsable de la correction floue ("fuzzy matching") des mots
transcrits par Whisper qui ressemblent fortement à un mot du
vocabulaire du menu, sans lui être identiques.

Utile pour rattraper les petites erreurs de reconnaissance vocale sur
des mots spécifiques à notre contexte (ex: "sausse angérienne"
reconnu à la place de "sauce Algérienne").
"""

import difflib

# Seuil de similarité (entre 0 et 1) au-delà duquel on considère
# qu'un mot transcrit correspond probablement à un mot du menu.
# Plus proche de 1 = correction plus prudente (moins de faux positifs,
# mais rate aussi plus d'erreurs réelles).
SIMILARITY_THRESHOLD = 0.75

# Longueur minimale d'un mot pour tenter une correction : les mots
# très courts (ex: "de", "un", "et") donnent des correspondances
# floues peu fiables et risqueraient d'être corrigés à tort.
MIN_WORD_LENGTH = 4


def _extract_vocabulary_words(menu: dict) -> set[str]:
    """
    Extrait tous les mots individuels du vocabulaire du menu (noms de
    produits, viandes, sauces, extras), utilisés comme référence pour
    la correction floue.
    """
    words = set()

    for category in menu["categories"]:
        for item in category["items"]:
            for word in item["name"].replace("-", " ").split():
                words.add(word)

        customization = category.get("customization", {})
        for meat in customization.get("meat_choices", []):
            for word in meat.split():
                words.add(word)
        for sauce in customization.get("sauces", []):
            for word in sauce.split():
                words.add(word)
        for extra in customization.get("extras", []):
            for word in extra["name"].split():
                words.add(word)

        # Mot fixe important : la ville de livraison, souvent mal
        # transcrite (ex: "Calabraise" au lieu de "Calais").
        words.add("Calais")

        return {word for word in words if len(word) >= MIN_WORD_LENGTH}


def correct_transcription(text: str, menu: dict) -> str:
    """
    Parcourt chaque mot de la transcription et le remplace par le mot
    du vocabulaire du menu le plus proche, si la ressemblance dépasse
    le seuil défini. Les mots déjà exacts, ou sans correspondance
    suffisamment proche, restent inchangés.
    """
    vocabulary_words = _extract_vocabulary_words(menu)

    corrected_words = []
    for word in text.split():
        # On retire la ponctuation collée au mot pour la comparaison,
        # mais on la remet ensuite pour ne pas abîmer la phrase.
        clean_word = word.strip(",.!?;:")

        if len(clean_word) < MIN_WORD_LENGTH:
            corrected_words.append(word)
            continue

        matches = difflib.get_close_matches(
            clean_word, vocabulary_words, n=1, cutoff=SIMILARITY_THRESHOLD
        )

        if matches and matches[0].lower() != clean_word.lower():
            corrected_words.append(word.replace(clean_word, matches[0]))
        else:
            corrected_words.append(word)

    return " ".join(corrected_words)


if __name__ == "__main__":
    from src.menu.loader import load_menu

    menu = load_menu()

    test_sentences = [
        "je voudrais une sausse angérienne",
        "avec du cheddare et des tenderes",
        "une pizza margarita",
    ]

    for sentence in test_sentences:
        corrected = correct_transcription(sentence, menu)
        print(f"Avant  : {sentence}")
        print(f"Après  : {corrected}\n")