"""
Module responsable de la gestion des sessions de conversation.

Une session = une conversation isolée entre un client et l'agent.
Stockage en mémoire (dictionnaire Python) pour ce prototype : suffisant
tant que l'API tourne sur un seul processus. Migration possible vers
Redis ou une base de données plus tard si besoin de scalabilité
(plusieurs serveurs, persistance entre redémarrages).
"""

import uuid

# Dictionnaire en mémoire : session_id -> données de la session.
# ATTENTION : ces données sont perdues si le serveur redémarre.
_sessions: dict[str, dict] = {}


def create_session(system_prompt: str) -> str:
    """
    Crée une nouvelle session de conversation, initialisée avec
    le prompt système (les instructions + le menu). Retourne
    l'identifiant unique de cette session.
    """
    session_id = str(uuid.uuid4())[:8]
    _sessions[session_id] = {
        "messages": [{"role": "system", "content": system_prompt}],
        "order_saved": False,
    }
    return session_id


def get_session(session_id: str) -> dict | None:
    """
    Retrouve les données d'une session existante par son identifiant.
    Retourne None si la session n'existe pas (id invalide ou expiré).
    """
    return _sessions.get(session_id)