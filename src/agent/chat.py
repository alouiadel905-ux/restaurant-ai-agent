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
from src.agent.confirmation_detector import looks_like_confirmation
from src.order.calculator import calculate_order_total
from src.order.storage import save_confirmed_order
from src.order.validation import validate_and_normalize_phone


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
- CONCISION OBLIGATOIRE (contexte téléphonique) : réponds toujours en 1 à 3 phrases courtes maximum, comme un vrai employé au téléphone pressé mais poli. N'énumère JAMAIS une liste complète d'options (toutes les viandes, tous les fromages, tous les suppléments, toutes les sauces) sauf si le client demande EXPLICITEMENT "quelles sont les options" ou "qu'est-ce que vous avez comme...". Pour une clarification, pose une question ciblée et courte (ex: "Quelle viande souhaitez-vous ?"), jamais une liste exhaustive.
- UNE SEULE QUESTION À LA FOIS : ne pose jamais plusieurs questions différentes dans la même réponse (ex: ne demande pas la viande ET les frites ET le sandwich en même temps). S'il manque plusieurs informations, demande-les une par une, dans l'ordre, en attendant la réponse du client avant de poser la suivante.
- NE FAIS PAS DE RÉCAPITULATIF NI DE TOTAL avant que le client ait clairement signalé qu'il a terminé de commander (ex: "c'est tout", "ce sera tout", "j'ai terminé", "c'est bon pour la commande"). Tant qu'il n'a pas dit ça, contente-toi de confirmer brièvement l'ajout en cours et de demander "Autre chose ?" — ne calcule et n'annonce aucun total avant ce signal explicite.
- POUR LES TAILLES DE TACOS À L'ORAL : ne dis JAMAIS les lettres "M", "L" ou "XL" à voix haute (elles se prononcent mal, notamment "XL" qui sonne comme un chiffre romain). Dis à la place le nombre de viandes directement : "un tacos à une viande", "un tacos à deux viandes", "un tacos à trois viandes". Idem en interne : ne pense JAMAIS en termes de "M/L/XL", raisonne uniquement en nombre de viandes.
- POUR LES TAILLES DE PIZZAS À L'ORAL : "Junior", "Senior" et "Mega" se prononcent bien, tu peux les dire normalement.
- N'utilise JAMAIS de mise en forme Markdown (pas d'astérisques, pas de tirets de liste, pas de titres, pas de tableaux). Réponds en texte brut, en phrases naturelles, comme à l'oral. Pour un récapitulatif, énonce les articles à la suite dans une phrase fluide plutôt qu'en liste.
- Reste concis et naturel, comme un vrai employé au téléphone, pas comme un robot qui récite une liste.
- Les prix doivent toujours correspondre exactement à ceux du menu.
- IMPORTANT sur les burgers et sandwichs : quand un prix "Seul" et un prix "Menu" sont indiqués, le prix "Menu" INCLUT DÉJÀ les frites et la boisson. Ne rajoute JAMAIS le prix d'une boisson ou de frites en plus du prix "Menu" — ce serait facturer deux fois la même chose. Le prix "Menu" est un prix final, tout compris.
- AVANT DE CONSIDÉRER UNE COMMANDE COMME TERMINÉE (c'est-à-dire une fois que le client a signalé explicitement qu'il a fini de commander), tu dois OBLIGATOIREMENT :
  1. Récapituler l'intégralité de la commande dans une phrase fluide et concise (chaque produit, taille, options, prix), sans mise en forme, comme si tu le disais à voix haute.
  2. Annoncer le montant total.
  3. Demander explicitement au client de confirmer ("Est-ce que je peux valider cette commande ?" ou équivalent).
  4. Attendre une réponse affirmative claire du client (ex: "oui", "c'est bon", "confirmé") avant de considérer la commande comme validée.
- Ne considère JAMAIS une commande comme confirmée sur la seule base d'un ajout de produit ou d'un silence — il faut une validation explicite et sans ambiguïté du client, après avoir vu le récapitulatif complet.
- Si le client modifie encore quelque chose après le récapitulatif, refais un récapitulatif à jour avant de redemander confirmation.
- Une fois la commande confirmée, demande le nom du client et un numéro de téléphone (nécessaires pour la préparation), sauf si déjà donnés.
- Le numéro de téléphone doit être un numéro français valide à 10 chiffres (ex: 06 12 34 56 78). Si le numéro donné ne fait pas 10 chiffres ou semble invalide, demande poliment au client de le répéter ou de le corriger AVANT de considérer la commande comme complète.
- LIVRAISON : le restaurant livre UNIQUEMENT à Calais, code postal 62100. Si le client demande une livraison, demande-lui SEULEMENT le numéro et le nom de la rue (ex: "48 rue de la Paix") — ne demande JAMAIS le code postal ni la ville, ils sont automatiquement 62100 Calais. Si le client mentionne une autre ville que Calais, informe-le poliment que le restaurant ne livre qu'à Calais.
- IMPORTANT sur les tacos : la taille (M/L/XL) est directement déterminée par le NOMBRE de viandes choisies : 1 viande = taille M, 2 viandes = taille L, 3 viandes = taille XL. Si le client précise le nombre de viandes ou énumère 2 ou 3 viandes différentes, DÉDUIS automatiquement la taille correspondante — ne redemande PAS la taille séparément, ce serait redondant et agaçant pour le client.
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
        if not order_already_saved and looks_like_confirmation(user_input):
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
                print(f"[Système] Commande enregistrée sous le numéro {saved['order_id']}\n")


if __name__ == "__main__":
    run_conversation()