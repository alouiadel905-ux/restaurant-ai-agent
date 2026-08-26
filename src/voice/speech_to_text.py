"""
Module responsable de la transcription audio -> texte (Speech-to-Text),
en utilisant faster-whisper (version optimisée CPU du modèle Whisper).

Le modèle est chargé une seule fois en mémoire (pas à chaque appel),
car son chargement est l'opération la plus lente.
"""

from faster_whisper import WhisperModel

# "base" : bon compromis vitesse/précision pour un CPU sans GPU dédié.
# Options possibles, du plus rapide au plus précis :
# tiny < base < small < medium < large-v3
MODEL_SIZE = "base"

# Le modèle n'est chargé qu'au premier appel (pas au chargement du
# fichier), pour ne pas ralentir le démarrage du programme si la
# transcription n'est pas utilisée dans cette exécution.
_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    """Charge le modèle Whisper une seule fois, puis le réutilise."""
    global _model
    if _model is None:
        # compute_type="int8" : quantification qui réduit la charge CPU
        # et la RAM utilisées, essentiel sans carte graphique dédiée.
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe_audio(audio_path: str, vocabulary_hint: str | None = None) -> str:
    """
    Transcrit un fichier audio (wav, mp3, m4a...) en texte français.
    Retourne le texte complet reconnu.

    vocabulary_hint : texte optionnel (ex: liste des produits du menu)
    donné à Whisper pour orienter la reconnaissance vers un vocabulaire
    attendu. Utile pour éviter les confusions sur des mots spécifiques
    à notre contexte (ex: "mayonnaise", "tacos", noms de sauces...).
    """
    model = _get_model()

    segments, info = model.transcribe(
        audio_path,
        language="fr",
        initial_prompt=vocabulary_hint,
    )

    # Whisper découpe la transcription en "segments" (phrases/passages).
    # On les recolle en un seul texte.
    full_text = " ".join(segment.text.strip() for segment in segments)

    return full_text.strip()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage : python -m src.voice.speech_to_text chemin/vers/fichier_audio.wav")
        sys.exit(1)

    audio_file = sys.argv[1]
    print(f"Transcription en cours de : {audio_file}")
    print("(le premier lancement peut être plus long, le temps de télécharger le modèle)\n")

    result = transcribe_audio(audio_file)
    print("Texte reconnu :")
    print(result)