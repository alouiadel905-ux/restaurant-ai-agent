"""
Module responsable du comportement conversationnel de l'agent
de prise de commande. Construit les instructions données à l'IA
(prompt système) et gère la boucle de conversation en terminal.
"""

import json

from src.llm.groq_client import get_client, send_message
from src.menu.loader import load_menu
from src.menu.formatter import format_menu_for_prompt
from src.agent.order_extractor import extract_order


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

Voici le menu complet du restaurant :

{menu_text}
"""


def run_conversation() -> None:
    """
    Lance une boucle de conversation dans le terminal entre
    l'utilisateur et l'agent. Tape 'quit' pour arrêter.
    Tape '/commande' pour voir la commande structurée extraite
    à partir de la conversation jusqu'ici.
    """
    client = get_client()
    menu = load_menu()
    menu_text = format_menu_for_prompt(menu)

    # L'historique de la conversation commence avec les instructions
    # système (invisibles pour l'utilisateur, mais lues par l'IA).
    messages = [
        {"role": "system", "content": build_system_prompt(menu_text)}
    ]

    print("=== Agent La Capital (tape 'quit' pour arrêter, '/commande' pour voir la commande extraite) ===\n")

    while True:
        user_input = input("Client : ").strip()

        if user_input.lower() in {"quit", "exit"}:
            print("Agent : Merci et à bientôt chez La Capital !")
            break

        if not user_input:
            continue

        # Commande spéciale de debug : affiche la commande structurée
        # extraite à partir de la conversation jusqu'ici.
        if user_input == "/commande":
            order = extract_order(client, messages, menu)
            print("\n--- Commande extraite ---")
            print(json.dumps(order, indent=2, ensure_ascii=False))
            print("--------------------------\n")
            continue

        # On ajoute le message du client à l'historique
        messages.append({"role": "user", "content": user_input})

        # On envoie tout l'historique à Groq et on récupère la réponse
        reply = send_message(client, messages)

        # On ajoute la réponse de l'IA à l'historique, pour qu'elle
        # se souvienne de ce qu'elle a dit lors du prochain échange
        messages.append({"role": "assistant", "content": reply})

        print(f"Agent : {reply}\n")


if __name__ == "__main__":
    run_conversation()