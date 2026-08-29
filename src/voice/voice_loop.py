"""
Boucle de conversation 100% vocale : micro -> transcription (Whisper)
-> agent (Groq) -> synthèse vocale (Piper) -> haut-parleur.

Assemble tous les modules construits en Phase 6, sur le même modèle
que la boucle texte de src/agent/chat.py.
"""

import json

from src.llm.groq_client import get_client, send_message, LLMUnavailableError
from src.menu.loader import load_menu
from src.menu.formatter import format_menu_for_prompt, build_vocabulary_hint
from src.agent.chat import build_system_prompt
from src.agent.confirmation_detector import looks_like_confirmation
from src.agent.order_extractor import extract_order
from src.order.calculator import calculate_order_total
from src.order.storage import save_confirmed_order
from src.order.validation import validate_and_normalize_phone
from src.voice.microphone import record_audio
from src.voice.speech_to_text import transcribe_audio
from src.voice.text_to_speech import speak
from src.voice.text_cleaning import strip_markdown_for_speech
from src.voice.vocabulary_correction import correct_transcription

RECORDING_DURATION_SECONDS = 12


def run_voice_conversation() -> None:
    """
    Lance une conversation entièrement vocale dans le terminal.
    Appuie sur Entrée pour parler, tape 'quit' + Entrée pour arrêter.
    """
    client = get_client()
    menu = load_menu()
    menu_text = format_menu_for_prompt(menu)
    vocabulary_hint = build_vocabulary_hint(menu)

    messages = [
        {"role": "system", "content": build_system_prompt(menu_text)}
    ]

    order_already_saved = False

    welcome_message = "Bonjour et bienvenue au restaurant La Capital ! Que puis-je vous préparer aujourd'hui ?"
    messages.append({"role": "assistant", "content": welcome_message})
    print(f"Agent : {welcome_message}")
    speak(strip_markdown_for_speech(welcome_message))

    print("\n(Appuie sur Entrée pour parler, tape 'quit' + Entrée pour arrêter)\n")

    while True:
        command = input("> ").strip().lower()

        if command == "quit":
            print("Agent : Merci et à bientôt chez La Capital !")
            break

        # Étape 1 : enregistrement du micro
        audio_path = record_audio(RECORDING_DURATION_SECONDS)

        # Étape 2 : transcription en texte, orientée par le vocabulaire du menu
        raw_text = transcribe_audio(str(audio_path), vocabulary_hint=vocabulary_hint)

        # Étape 2bis : correction floue des mots proches du vocabulaire
        # du menu (ex: "sausse angérienne" -> "sauce Algérienne").
        user_text = correct_transcription(raw_text, menu)

        if user_text != raw_text:
            print(f"Client (transcrit brut) : {raw_text}")
        print(f"Client (transcrit) : {user_text}")

        if not user_text:
            print("Agent : Je n'ai rien entendu, peux-tu répéter ?")
            continue

        messages.append({"role": "user", "content": user_text})

        # Étape 3 : réponse de l'agent (texte)
        try:
            reply = send_message(client, messages)
        except LLMUnavailableError as e:
            print(f"Agent : Problème technique ({e}). Réessaie dans un instant.")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": reply})
        print(f"Agent : {reply}")

        # Étape 4 : synthèse vocale + lecture de la réponse (nettoyée
        # du Markdown, pour éviter que Piper ne lise les symboles).
        speak(strip_markdown_for_speech(reply))

        # Sauvegarde automatique de la commande confirmée (même logique
        # que dans chat.py et l'API). On n'appelle l'extraction (coûteuse
        # en quota API) que si le message ressemble à une confirmation,
        # pas après chaque message.
        if not order_already_saved and looks_like_confirmation(user_text):
            order = extract_order(client, messages, menu)

            is_confirmed = order.get("status") == "confirmed"
            valid_phone = validate_and_normalize_phone(order.get("customer_phone"))
            has_contact_info = bool(order.get("customer_name")) and bool(valid_phone)
            has_items = len(order.get("items", [])) > 0

            if is_confirmed and has_contact_info and has_items:
                verified = calculate_order_total(order, menu)
                saved = save_confirmed_order(
                    verified,
                    customer_name=order.get("customer_name"),
                    customer_phone=valid_phone,
                )
                order_already_saved = True
                print(f"[Système] Commande enregistrée sous le numéro {saved['order_id']}")


if __name__ == "__main__":
    run_voice_conversation()
