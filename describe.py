"""
Calls a local Ollama vision model (Qwen2.5-VL) to describe a clothing photo.
Returns a French description and a compact keyword string.
"""

import json
import base64
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5vl:7b"  # change to qwen2.5vl:3b if you want lighter

PROMPT = """Tu es un expert en mode et en revente sur Vinted.
Analyse cette photo d'un vêtement et réponds UNIQUEMENT avec un JSON valide,
sans texte autour, sans backticks, au format exact:

{
  "description_fr": "Phrase descriptive en français, 1-2 phrases, mentionne type, couleur, matière apparente, coupe, état visible.",
  "keywords": "5 à 8 mots-clés séparés par des espaces, en français, optimisés pour une recherche sur Vinted (type vêtement, couleur, marque si visible, style, matière)"
}
"""


def describe_image(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": PROMPT,
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=300,
    )
    resp.raise_for_status()
    raw = resp.json().get("response", "").strip()

    # Strip accidental code fences
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: dump raw text into both fields
        data = {"description_fr": raw, "keywords": raw[:80]}

    return {
        "description_fr": data.get("description_fr", "").strip(),
        "keywords": data.get("keywords", "").strip(),
    }
