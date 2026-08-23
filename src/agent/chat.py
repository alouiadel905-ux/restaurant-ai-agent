"""
Module responsable du comportement conversationnel de l'agent
de prise de commande. Construit les instructions données à l'IA
(prompt système) et gère la boucle de conversation en terminal.
"""

import json

from src.llm.groq_client import get_client, send_message, LLMUnavailableError
from src.menu.loader import load_menu
from src.menu.formatter import format_menu_for_prompt
from src.agent.order_extractor import extract_order
from src.order.calculator import calculate_order_total
from src.order.storage import save_confirmed_order


def build_system_prompt(menu_text: str) -> str:
    """
    Construit le prompt système : les instructions données à l'IA
    pour définir son rôle, son comportement, et lui fournir le menu.

    C'est ce texte qui "programme" la personnalité et les règles
    de l'agent, avant même que le client ne dise quoi que ce soit.
    """
    return f"""Tu es l'agent téléphonique du restaurant La Capital, à Calais.
Tu prends les commandes des clients par téléphone, de façon naturelle et chaleureuse.

RÈGLES IMPORTANTES :
- Tu ne connais QUE les produits listés dans le menu ci-dessous. N'invente jamais un produit qui n'y figure pas.
- Si un client demande un produit qui n'existe pas, dis-le clairement et propose une alternative proche du menu.
- Si une demande est ambiguë (taille non précisée, choix de viande manquant pour un tacos, etc.), pose une question de clarification avant de continuer.
- Reste concis et naturel, comme un vrai employé au téléphone, pas comme un robot qui récite une liste.
- Les prix doivent toujours correspondre exactement à ceux du menu.
- IMPORTANT sur les burgers et sandwichs : quand un prix "Seul" et un prix "Menu" sont indiqués, le prix "Menu" INCLUT DÉJÀ les frites et la boisson. Ne rajoute JAMAIS le prix d'une boisson ou de frites en plus du prix "Menu" — ce serait facturer deux fois la même chose. Le prix "Menu" est un prix final, tout compris.
- AVANT DE CONSIDÉRER UNE COMMANDE COMME TERMINÉE, tu dois OBLIGATOIREMENT :
  1. Récapituler l'intégralité de la commande (chaque produit, taille, options, prix), sous forme de liste claire.
  2. Annoncer le montant total.
  3. Demander explicitement au client de confirmer ("Est-ce que je peux valider cette commande ?" ou équivalent).
  4. Attendre une réponse affirmative claire du client (ex: "oui", "c'est bon", "confirmé") avant de considérer la commande comme validée.
- Ne considère JAMAIS une commande comme confirmée sur la seule base d'un ajout de produit ou d'un silence — il faut une validation explicite et sans ambiguïté du client, après avoir vu le récapitulatif complet.
- Si le client modifie encore quelque chose après le récapitulatif, refais un récapitulatif à jour avant de redemander confirmation.
- Une fois la commande confirmée, demande le nom du client et un numéro de téléphone (nécessaires pour la préparation), sauf si déjà donnés.
- Ne considère jamais qu'une commande est valide si elle ne contient aucun produit : si le client tente de confirmer sans avoir rien commandé, explique-lui poliment qu'il doit d'abord choisir au moins un produit.

Voici le menu complet du restaurant :

{menu_text}
"""


def run_conversation() -> None:
    """
    Lance une boucle de conversation dans le terminal entre
    l'utilisateur et l'agent. Tape 'quit' pour arrêter.
    Tape '/commande' pour voir la commande extraite par l'IA.
    Tape '/total' pour voir la commande vérifiée par le calcul Python.

    Dès que le client confirme sa commande ET donne ses coordonnées,
    elle est automatiquement sauvegardée dans data/orders.json.

    Résistant aux pannes : si l'IA est temporairement indisponible
    (réseau, quota), le client reçoit un message clair au lieu
    d'un plantage du programme.
    """
    client = get_client()
    menu = load_menu()
    menu_text = format_menu_for_prompt(menu)

    messages = [
        {"role": "system", "content": build_system_prompt(menu_text)}
    ]

    order_already_saved = False

    print("=== Agent La Capital (tape 'quit' pour arrêter, '/commande' ou '/total') ===\n")

    while True:
        user_input = input("Client : ").strip()

        if user_input.lower() in {"quit", "exit"}:
            print("Agent : Merci et à bientôt chez La Capital !")
            break

        if not user_input:
            continue

        if user_input == "/commande":
            order = extract_order(client, messages, menu)
            print("\n--- Commande extraite (par l'IA) ---")
            print(json.dumps(order, indent=2, ensure_ascii=False))
            print("--------------------------------------\n")
            continue

        if user_input == "/total":
            order = extract_order(client, messages, menu)
            verified = calculate_order_total(order, menu)
            print("\n--- Commande vérifiée (calcul Python) ---")
            print(json.dumps(verified, indent=2, ensure_ascii=False))
            print("------------------------------------------\n")
            continue

        messages.append({"role": "user", "content": user_input})

        # On protège l'appel principal : si l'IA est indisponible,
        # le client reçoit un message clair, la conversation continue
        # au lieu de planter (le message utilisateur reste en historique
        # pour être retraité au prochain tour).
        try:
            reply = send_message(client, messages)
        except LLMUnavailableError as e:
            print(f"Agent : Désolé, un problème technique m'empêche de répondre "
                  f"pour le moment ({e}). Peux-tu répéter dans quelques instants ?\n")
            messages.pop()  # on retire le message non traité pour éviter un historique incohérent
            continue

        messages.append({"role": "assistant", "content": reply})
        print(f"Agent : {reply}\n")

        # Après chaque échange, on vérifie discrètement si la commande
        # vient d'être confirmée ET que les coordonnées du client sont
        # connues, pour la sauvegarder automatiquement une seule fois.
        # On vérifie aussi qu'il y a bien au moins un produit : une
        # commande "confirmée" mais vide ne doit jamais être enregistrée.
        if not order_already_saved:
            order = extract_order(client, messages, menu)

            is_confirmed = order.get("status") == "confirmed"
            has_contact_info = order.get("customer_name") and order.get("customer_phone")
            has_items = len(order.get("items", [])) > 0

            if is_confirmed and has_contact_info and has_items:
                verified = calculate_order_total(order, menu)
                saved = save_confirmed_order(
                    verified,
                    customer_name=order.get("customer_name"),
                    customer_phone=order.get("customer_phone"),
                )
                order_already_saved = True
                print(f"[Système] Commande enregistrée sous le numéro {saved['order_id']}\n")


if __name__ == "__main__":
    run_conversation()