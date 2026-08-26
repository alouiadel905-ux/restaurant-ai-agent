"""
Module responsable de l'enregistrement audio depuis le microphone.
"""

from pathlib import Path

import sounddevice as sd
import soundfile as sf

# 16000 Hz : fréquence d'échantillonnage recommandée pour Whisper
# (pas besoin de plus, ça alourdirait le fichier pour rien).
SAMPLE_RATE = 16000

RECORDING_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "voices" / "_recording.wav"


def record_audio(duration_seconds: int, output_path: Path = RECORDING_PATH) -> Path:
    """
    Enregistre l'audio du micro pendant une durée fixe, et le
    sauvegarde en fichier .wav. Bloquant : la fonction attend la
    fin de l'enregistrement avant de continuer.
    """
    print(f"🎙️  Enregistrement... ({duration_seconds}s, parle maintenant)")

    recording = sd.rec(
        int(duration_seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()  # attend que l'enregistrement soit terminé

    sf.write(str(output_path), recording, SAMPLE_RATE)
    print("✅ Enregistrement terminé.")

    return output_path


if __name__ == "__main__":
    path = record_audio(duration_seconds=5)
    print(f"Fichier sauvegardé : {path}")