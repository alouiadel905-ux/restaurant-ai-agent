"""
Module responsable de la synthèse vocale (Text-to-Speech), en
utilisant Piper (moteur léger, open source, optimisé CPU).

Génère un fichier audio .wav à partir d'un texte, et peut le lire
directement via winsound (module natif Windows, pas de dépendance
supplémentaire nécessaire pour la lecture).
"""

import os
import subprocess
import winsound
from pathlib import Path

VOICE_MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "voices" / "fr_FR-siwis-medium.onnx"
)

# Fichier temporaire réutilisé à chaque synthèse (pas besoin de
# garder un historique de fichiers audio pour l'instant).
OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "voices" / "_last_reply.wav"


def synthesize_speech(text: str, output_path: Path = OUTPUT_PATH) -> Path:
    """
    Génère un fichier audio .wav à partir d'un texte, en utilisant
    la voix française chargée depuis VOICE_MODEL_PATH.

    Retourne le chemin du fichier audio généré.
    """
    if not VOICE_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modèle de voix introuvable : {VOICE_MODEL_PATH}. "
            "Vérifie que les fichiers .onnx et .onnx.json sont bien "
            "dans data/voices/."
        )

    # Sur Windows, un sous-processus peut interpréter le texte reçu
    # avec l'encodage régional (souvent cp1252) au lieu d'UTF-8, ce
    # qui corrompt tout le texte après le premier caractère accentué.
    # On force explicitement l'environnement du sous-processus à
    # utiliser UTF-8, pour que les accents français soient bien gérés.
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    subprocess.run(
        ["piper", "--model", str(VOICE_MODEL_PATH), "--output_file", str(output_path)],
        input=text.encode("utf-8"),
        check=True,
        env=env,
    )

    return output_path


def play_audio(audio_path: Path) -> None:
    """
    Joue un fichier .wav via le module natif Windows winsound.
    Bloquant : la fonction attend la fin de la lecture avant de continuer.
    """
    winsound.PlaySound(str(audio_path), winsound.SND_FILENAME)


def speak(text: str) -> None:
    """
    Fonction pratique : génère la voix ET la joue directement.
    C'est celle qu'on utilisera dans le reste du projet.
    """
    audio_path = synthesize_speech(text)
    play_audio(audio_path)


if __name__ == "__main__":
    test_text = "Bonjour et bienvenue au restaurant La Capital. Que puis-je vous préparer aujourd'hui ?"
    print(f"Synthèse et lecture de : {test_text}")
    speak(test_text)
    print("Terminé.")