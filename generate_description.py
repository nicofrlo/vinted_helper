"""
Build an optimised Vinted description prompt and copy it to clipboard,
then open ChatGPT in the browser so the user can paste it.
"""

from __future__ import annotations

import subprocess
import sys
import webbrowser

SYSTEM_CONTEXT = (
    "Tu es un expert en rédaction d'annonces Vinted optimisées pour la vente. "
    "Tu rédiges en français, avec un ton sympathique et professionnel. "
    "Tu utilises des mots-clés pertinents pour le référencement sur Vinted. "
    "Tu ne mens jamais sur l'état ou les défauts du vêtement.\n\n"
)


def _build_prompt(
    image_description: str,
    keywords: str,
    user_answers: dict,
    similar_listings: list[dict],
) -> str:
    parts: list[str] = [SYSTEM_CONTEXT]

    if image_description:
        parts.append("## Description de la photo du vêtement")
        parts.append(image_description or "(non disponible)")

    if keywords:
        parts.append("\n## Mots-clés identifiés")
        parts.append(keywords)

    # Guided answers
    answers_lines = []
    labels = {
        "etat": "État",
        "categorie": "Catégorie",
        "public": "Public",
        "coupe": "Coupe",
        "matiere": "Matière",
        "defauts": "Défauts",
        "defauts_detail": "Détail défauts",
        "raison": "Raison de vente",
        "negociation": "Négociation",
        "style": "Style",
    }
    for key, label in labels.items():
        val = user_answers.get(key, "")
        if val and val != "Non précisé":
            answers_lines.append(f"- {label} : {val}")

    if answers_lines:
        parts.append("\n## Informations fournies par le vendeur")
        parts.extend(answers_lines)

    # Similar listings for inspiration
    descs = []
    for item in similar_listings:
        desc = item.get("description", "")
        title = item.get("title", "")
        if desc:
            descs.append(f'- "{title}" : {desc[:300]}')
        elif title:
            descs.append(f'- "{title}"')
    if descs:
        parts.append("\n## Annonces similaires sur Vinted (pour inspiration)")
        parts.extend(descs[:5])

    parts.append(
        "\n## Consigne\n"
        "Rédige une description Vinted optimisée pour cet article.\n"
        "N'en fait pas trop reste naturel et concis\n"
        "- 2 à 4 phrases maximum\n"
        "- Mentionne l'état, la matière, la coupe, le style si connus\n"
        "- Si des défauts sont mentionnés, les intégrer honnêtement\n"
        "- Inclus des mots-clés naturellement pour le référencement\n"
        "- Termine par une phrase engageante (ex: invitation à poser des questions)\n"
        "- Ne mets PAS le prix dans la description\n"
        "- Format : texte brut, pas de markdown, pas d'emojis excessifs"
    )
    return "\n".join(parts)


def _copy_to_clipboard(text: str):
    """Copy text to system clipboard (macOS)."""
    if sys.platform == "darwin":
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
    else:
        # Linux / xclip fallback
        subprocess.run(
            ["xclip", "-selection", "clipboard"], input=text.encode(), check=True
        )


def generate_vinted_prompt(
    image_description: str,
    keywords: str,
    user_answers: dict,
    similar_listings: list[dict],
) -> str:
    """Build the prompt, copy it to clipboard, and open ChatGPT."""
    prompt = _build_prompt(image_description, keywords, user_answers, similar_listings)
    _copy_to_clipboard(prompt)
    webbrowser.open("https://chatgpt.com")
    return prompt
