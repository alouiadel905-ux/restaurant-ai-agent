"""
Module responsable de la communication avec l'API Groq.

Isole les détails techniques (clé API, nom du modèle, appel HTTP)
du reste du code, pour que le reste du projet n'ait qu'à appeler
send_message() sans se soucier de "comment" ça parle à Groq.
"""

import os
from dotenv import load_dotenv
from groq import Groq

# Nom du modèle utilisé pour toutes les conversations de l'agent.
# Centralisé ici pour ne le changer qu'à un seul endroit si besoin.
MODEL_NAME = "llama-3.3-70b-versatile"


def get_client() -> Groq:
    """
    Charge la clé API depuis le fichier .env et retourne
    un client Groq prêt à l'emploi.

    Lève une erreur claire si la clé est manquante, plutôt que
    de laisser une erreur technique confuse remonter plus tard.
    """
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY introuvable. Vérifie que ton fichier .env "
            "existe à la racine du projet et contient bien la clé."
        )

    return Groq(api_key=api_key)


def send_message(client: Groq, messages: list[dict]) -> str:
    """
    Envoie l'historique complet de la conversation à Groq
    et retourne uniquement le texte de la réponse.

    messages : liste de dictionnaires au format
               {"role": "system"/"user"/"assistant", "content": "..."}
    """
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
    )
    return response.choices[0].message.content