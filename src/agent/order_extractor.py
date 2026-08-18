"""
Module responsable de l'extraction d'une commande structurée
(format JSON) à partir de l'historique d'une conversation.

Utilise un appel IA séparé de la conversation principale, dédié
uniquement à cette tâche d'analyse et de structuration.
"""

import json
from groq import Groq

from src.llm.groq_client import MODEL_NAME
from src.menu.formatter import format_menu_with_ids


def _build_extraction_prompt(menu_text_with_ids: str) -> str:
    """
    Construit les instructions données à l'IA pour la tâche
    d'extraction. Contrairement au prompt conversationnel, celui-ci
    doit être strict : on ne veut QUE du JSON en sortie, rien d'autre.
    """
    return f"""Tu es un système d'extraction de données. Ta seule tâche est de lire une conversation entre un client et un agent de restaurant, et d'en extraire la commande sous forme de JSON STRICT.

Voici le menu du restaurant, avec les identifiants techniques (id) à utiliser obligatoirement :

{menu_text_with_ids}

RÈGLES :
- Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, sans balises markdown.
- Utilise exactement le format suivant :
{{
  "items": [
    {{
      "item_id": "identifiant_exact_du_menu",
      "name": "Nom lisible du produit",
      "quantity": 1,
      "size": "nom de la taille choisie, ou null si non applicable",
      "extras": ["liste des extras demandés, vide si aucun"],
      "sauces": ["liste des sauces demandées, vide si aucune"],
      "unit_price": 0.00
    }}
  ],
  "status": "in_progress"
}}
- "item_id" doit correspondre EXACTEMENT à un id présent dans le menu ci-dessus.
- "unit_price" doit être le prix correspondant à la taille choisie (ou le prix simple si pas de taille).
- Si le client n'a encore rien commandé de clair, retourne une liste "items" vide.
- Si une information nécessaire n'est pas encore connue (ex: taille non précisée), ne l'invente pas : mets null.
- "status" vaut "confirmed" uniquement si le client a explicitement validé sa commande, sinon "in_progress".
"""


def _build_transcript(messages: list[dict]) -> str:
    """
    Transforme l'historique de conversation (liste de messages
    avec role/content) en un texte simple lisible, en ignorant
    le message système (qui contient le prompt, pas la conversation).
    """
    lines = []
    for message in messages:
        if message["role"] == "system":
            continue
        speaker = "Client" if message["role"] == "user" else "Agent"
        lines.append(f"{speaker} : {message['content']}")
    return "\n".join(lines)


def extract_order(client: Groq, conversation_messages: list[dict], menu: dict) -> dict:
    """
    Analyse l'historique de conversation et retourne la commande
    structurée sous forme de dictionnaire Python.
    """
    menu_text_with_ids = format_menu_with_ids(menu)
    transcript = _build_transcript(conversation_messages)

    extraction_messages = [
        {"role": "system", "content": _build_extraction_prompt(menu_text_with_ids)},
        {"role": "user", "content": f"Voici la conversation à analyser :\n\n{transcript}"},
    ]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=extraction_messages,
        response_format={"type": "json_object"},
    )

    raw_content = response.choices[0].message.content
    return json.loads(raw_content)