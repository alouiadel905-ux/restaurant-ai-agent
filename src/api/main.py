"""
Application FastAPI exposant l'agent de prise de commande
du restaurant La Capital comme un service HTTP.

Lancer avec : uvicorn src.api.main:app --reload
Documentation interactive générée automatiquement sur :
http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.llm.groq_client import get_client, send_message, LLMUnavailableError
from src.menu.loader import load_menu
from src.menu.formatter import format_menu_for_prompt
from src.agent.chat import build_system_prompt
from src.agent.order_extractor import extract_order
from src.agent.confirmation_detector import looks_like_confirmation
from src.order.calculator import calculate_order_total
from src.order.storage import save_confirmed_order
from src.order.validation import validate_and_normalize_phone
from src.api.sessions import create_session, get_session

app = FastAPI(title="La Capital - Agent IA Restaurant")

# Autorise notre future page web de test (ouverte en local) à
# contacter cette API. En production, on restreindrait cette liste
# aux domaines réellement autorisés plutôt que d'ouvrir à tous ("*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ces éléments sont chargés UNE SEULE FOIS au démarrage du serveur
# (le menu ne change pas entre deux requêtes, pas besoin de le
# recharger à chaque appel).
client = get_client()
menu = load_menu()
SYSTEM_PROMPT = build_system_prompt(format_menu_for_prompt(menu))


class ChatRequest(BaseModel):
    """Format attendu du corps de la requête POST /chat."""
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    """Format de la réponse renvoyée par POST /chat."""
    session_id: str
    reply: str
    order_confirmed: bool


@app.get("/health")
def health_check():
    """Route simple pour vérifier que le serveur tourne."""
    return {"status": "ok", "restaurant": menu["restaurant"]}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Route principale : envoie un message de l'utilisateur à l'agent
    et retourne sa réponse.

    Si "session_id" n'est pas fourni, une nouvelle conversation est
    créée. Sinon, le message est ajouté à la conversation existante.
    """
    # Récupération ou création de la session
    if request.session_id:
        session = get_session(request.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session inconnue ou expirée.")
        session_id = request.session_id
    else:
        session_id = create_session(SYSTEM_PROMPT)
        session = get_session(session_id)

    session["messages"].append({"role": "user", "content": request.message})

    try:
        reply = send_message(client, session["messages"])
    except LLMUnavailableError as e:
        session["messages"].pop()  # on retire le message non traité
        raise HTTPException(status_code=503, detail=str(e))

    session["messages"].append({"role": "assistant", "content": reply})

    # Vérification et sauvegarde automatique si la commande est
    # confirmée et complète (même logique que dans chat.py terminal).
    # On n'appelle l'extraction que si le message ressemble à une
    # confirmation, pour économiser le quota API.
    order_confirmed = False

    if not session["order_saved"] and looks_like_confirmation(request.message):
        order = extract_order(client, session["messages"], menu)

        is_confirmed = order.get("status") == "confirmed"
        valid_phone = validate_and_normalize_phone(order.get("customer_phone"))
        has_contact_info = bool(order.get("customer_name")) and bool(valid_phone)
        has_items = len(order.get("items", [])) > 0

        if is_confirmed and has_contact_info and has_items:
            verified = calculate_order_total(order, menu)
            save_confirmed_order(
                verified,
                customer_name=order.get("customer_name"),
                customer_phone=valid_phone,
            )
            session["order_saved"] = True
            order_confirmed = True

    return ChatResponse(session_id=session_id, reply=reply, order_confirmed=order_confirmed)