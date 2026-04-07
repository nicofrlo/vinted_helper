"""
Vinted Seller Helper
--------------------
Upload a photo of a clothing item and get:
  1. A description + keywords generated locally by Qwen2.5-VL via Ollama
  2. Visually similar Vinted listings (with prices) via Vinted's photo search
  3. Candidate "worn by model" photos from Google Images

Run with:  streamlit run app.py
"""

import os
import tempfile
import time

import streamlit as st

from generate_description import _build_prompt

# from describe import describe_image
from vinted_search import vinted_image_search

st.set_page_config(page_title="Vinted Seller Helper", layout="wide")
st.title("👗 Vinted Seller Helper")
st.caption("Upload a photo or paste from clipboard (Ctrl+V / Cmd+V).")

# ---- Image input: file uploader + paste via JS ----
uploaded = st.file_uploader(
    "Photo of the clothing item",
    type=["jpg", "jpeg", "png", "webp"],
)

# Inject JS to listen for paste on the main Streamlit page and feed the
# pasted image into the file uploader's hidden <input type="file">.
st.components.v1.html(
    """
<script>
var parentDoc = window.parent.document;
if (!parentDoc._pasteListenerAdded) {
    parentDoc._pasteListenerAdded = true;
    parentDoc.addEventListener("paste", function(e) {
        var items = e.clipboardData.items;
        for (var i = 0; i < items.length; i++) {
            if (items[i].type.startsWith("image/")) {
                var file = items[i].getAsFile();
                var ext = file.type.split("/")[1] || "png";
                if (ext === "jpeg") ext = "jpg";
                var renamed = new File([file], "pasted_image." + ext, {type: file.type});
                var input = parentDoc.querySelector('input[type="file"]');
                if (input) {
                    var dt = new DataTransfer();
                    dt.items.add(renamed);
                    input.files = dt.files;
                    input.dispatchEvent(new Event("change", {bubbles: true}));
                }
                e.preventDefault();
                return;
            }
        }
    });
}
</script>
""",
    height=0,
)

n_vinted = st.slider("How many Vinted comparables", 5, 30, 15)

# use_llm = st.checkbox(
#     "Generate description with local LLM (Qwen2.5-VL)",
#     value=True,
#     help="Uncheck to skip Ollama. You'll type the keywords yourself for the Google Images search.",
# )

# ---- Guided questions for description generation ----
with st.expander(
    "📋 Caractéristiques du vêtement (pour générer la description)", expanded=True
):
    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1:
        q_etat = st.selectbox(
            "État",
            [
                "Non précisé",
                "Neuf avec étiquette",
                "Neuf sans étiquette",
                "Très bon état",
                "Bon état",
                "Satisfaisant",
            ],
            key="q_etat",
        )
        q_categorie = st.selectbox(
            "Catégorie",
            [
                "Non précisé",
                "Haut",
                "Bas",
                "Robe",
                "Veste / Manteau",
                "Chaussures",
                "Accessoire",
                "Sport",
            ],
            key="q_categorie",
        )
        q_public = st.selectbox(
            "Public",
            [
                "Non précisé",
                "Femme",
                "Homme",
                "Enfant",
                "Unisexe",
            ],
            key="q_public",
        )
    with q_col2:
        q_coupe = st.selectbox(
            "Coupe",
            [
                "Non précisé",
                "Ajusté (slim)",
                "Regular",
                "Oversize",
                "Crop",
            ],
            key="q_coupe",
        )
        q_matiere = st.selectbox(
            "Matière",
            [
                "Non précisé",
                "Coton",
                "Polyester",
                "Laine",
                "Lin",
                "Soie",
                "Cuir",
                "Synthétique",
                "Ne sait pas",
            ],
            key="q_matiere",
        )
        q_style = st.selectbox(
            "Style",
            [
                "Non précisé",
                "Casual",
                "Chic",
                "Streetwear",
                "Bohème",
                "Vintage",
                "Bureau",
                "Soirée",
            ],
            key="q_style",
        )
    with q_col3:
        q_defauts = st.selectbox(
            "Défauts",
            [
                "Aucun",
                "Bouloches légères",
                "Petite tache",
                "Accroc",
                "Décoloration",
            ],
            key="q_defauts",
        )
        q_defauts_detail = st.text_input(
            "Précision défauts (optionnel)", key="q_defauts_detail"
        )
        q_raison = st.selectbox(
            "Raison de vente",
            [
                "Non précisé",
                "Ne correspond plus à ma taille",
                "Jamais porté",
                "Changement de style",
                "Désencombrement",
            ],
            key="q_raison",
        )
        q_negociation = st.selectbox(
            "Négociation",
            [
                "Non précisé",
                "Prix négociable",
                "Prix ferme",
            ],
            key="q_negociation",
        )

user_answers = {
    "etat": q_etat,
    "categorie": q_categorie,
    "public": q_public,
    "coupe": q_coupe,
    "matiere": q_matiere,
    "style": q_style,
    "defauts": q_defauts,
    "defauts_detail": q_defauts_detail,
    "raison": q_raison,
    "negociation": q_negociation,
}

# Save uploaded file early so clipboard copy + Vinted both use it
image_path = None
if uploaded is not None:
    suffix = os.path.splitext(uploaded.name)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        image_path = tmp.name

col_go, col_lens = st.columns([1, 1])
with col_go:
    go = st.button("🔍 Analyze", type="primary", disabled=uploaded is None)
with col_lens:
    st.link_button(
        "🔍 Open Google Lens", "https://lens.google.com", disabled=image_path is None
    )

# ---------- Run analysis on button click ----------
if go and image_path is not None:
    left, right = st.columns([1, 2])
    with left:
        st.image(uploaded, caption="Your photo", width="stretch")

    # with right:
    #     if use_llm:
    #         with st.spinner("Describing the item with Qwen2.5-VL (local)..."):
    #             try:
    #                 desc = describe_image(image_path)
    #                 st.session_state["qwen_desc"] = desc
    #             except Exception as e:
    #                 st.error(f"Ollama / Qwen2.5-VL failed: {e}")

    with st.status("Searching Vinted...", expanded=True) as status:
        try:
            t0 = time.time()
            vinted_results = vinted_image_search(
                image_path,
                limit=n_vinted,
                on_status=lambda msg: status.update(label=msg),
                fetch_descriptions=5,
            )
            elapsed = time.time() - t0
            status.update(
                label=f"Done — {len(vinted_results)} results in {elapsed:.1f}s",
                state="complete",
            )
            st.session_state["vinted_results"] = vinted_results
        except Exception as e:
            st.error(f"Vinted search failed: {e}")
            status.update(label="Vinted search failed", state="error")

# ---------- Display results from session state ----------
# desc = st.session_state.get("qwen_desc")
# if desc:
#     st.divider()
#     st.subheader("📝 Description")
#     st.write(desc["description_fr"])
#     st.code(desc["keywords"], language=None)
#     st.caption("☝️ Copy these keywords into your Vinted listing title/description.")

vinted_results = st.session_state.get("vinted_results", [])
if vinted_results:
    st.divider()
    st.subheader("💶 Comparable Vinted listings")
    prices = [r["price_eur"] for r in vinted_results if r.get("price_eur")]
    if prices:
        c1, c2, c3 = st.columns(3)
        c1.metric("Median price", f"{sorted(prices)[len(prices) // 2]:.2f} €")
        c2.metric("Min", f"{min(prices):.2f} €")
        c3.metric("Max", f"{max(prices):.2f} €")

    cols = st.columns(5)
    for i, item in enumerate(vinted_results):
        with cols[i % 5]:
            if item.get("thumbnail"):
                st.image(item["thumbnail"], width="stretch")
            st.markdown(f"**{item.get('price_eur', '?')} €**")
            st.caption(f"{item.get('title', '')[:40]}")
            if item.get("brand"):
                st.caption(f"_{item['brand']}_  ·  size {item.get('size', '?')}")
            st.markdown(f"[Open ↗]({item['url']})")

    # ---------- Generate prompt & open ChatGPT ----------
    st.divider()
    st.subheader("✨ Générer la description Vinted")

    # Build prompt eagerly so we can embed it in JS
    _qwen = st.session_state.get("qwen_desc", {})
    _prompt_text = _build_prompt(
        image_description=_qwen.get("description_fr", ""),
        keywords=_qwen.get("keywords", ""),
        user_answers=user_answers,
        similar_listings=vinted_results,
    )
    st.session_state["generated_prompt"] = _prompt_text

    import json

    _escaped = json.dumps(_prompt_text)

    # --- Primary: generate description directly via Puter.js ---
    st.components.v1.html(
        f"""
    <script src="https://js.puter.com/v2/"></script>
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ font-family: "Source Sans Pro", sans-serif; padding: 8px; }}
      #generate-btn {{
        padding: 10px 24px; border-radius: 8px; border: none;
        cursor: pointer; font-size: 16px; background: #FF4B4B;
        color: white; font-weight: 600;
      }}
      #generate-btn:disabled {{ opacity: 0.6; cursor: wait; }}
      #loading {{ display: none; margin-top: 12px; color: #555; }}
      #loading .spinner {{
        display: inline-block; width: 18px; height: 18px;
        border: 3px solid #ddd; border-top: 3px solid #FF4B4B;
        border-radius: 50%; animation: spin 0.8s linear infinite;
        vertical-align: middle; margin-right: 8px;
      }}
      @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
      #result-container {{ display: none; margin-top: 14px; }}
      #result-text {{
        background: #f7f7f8; border: 1px solid #e0e0e0; border-radius: 8px;
        padding: 14px; white-space: pre-wrap; line-height: 1.5;
        font-size: 14px; max-height: 350px; overflow-y: auto;
      }}
      #copy-result-btn {{
        margin-top: 8px; padding: 6px 16px; border-radius: 6px;
        border: 1px solid #ccc; cursor: pointer; font-size: 14px;
        background: #f0f0f0;
      }}
      #error-container {{ display: none; margin-top: 12px; color: #d32f2f; }}
      #error-container button {{
        margin-top: 6px; padding: 6px 14px; border-radius: 6px;
        border: 1px solid #ccc; cursor: pointer; background: #f0f0f0;
      }}
    </style>

    <div id="auth-status" style="margin-bottom:10px; font-size:14px; color:#888;"></div>
    <button id="generate-btn">✨ Generer la description avec l'IA</button>
    <div id="loading"><span class="spinner"></span> Generation en cours...</div>
    <div id="result-container">
      <div id="result-text"></div>
      <button id="copy-result-btn">📋 Copier la description</button>
    </div>
    <div id="error-container"></div>

    <script>
    const prompt = {_escaped};

    // Check auth status on load and show it
    (async function() {{
      if (typeof puter === "undefined") return;
      try {{
        const user = await puter.auth.getUser();
        if (user && user.username) {{
          document.getElementById("auth-status").innerHTML =
            "✅ Connecte a Puter en tant que <b>" + user.username + "</b>";
        }}
      }} catch(e) {{
        // Not signed in yet — that's fine, we'll handle it on click
      }}
    }})();

    document.getElementById("generate-btn").addEventListener("click", async function() {{
      const btn = this;
      const loading = document.getElementById("loading");
      const resultContainer = document.getElementById("result-container");
      const errorContainer = document.getElementById("error-container");
      const authStatus = document.getElementById("auth-status");

      if (typeof puter === "undefined") {{
        errorContainer.innerHTML = "Le service Puter.js n'a pas pu se charger. Utilisez l'option ChatGPT ci-dessous.";
        errorContainer.style.display = "block";
        return;
      }}

      btn.disabled = true;
      errorContainer.style.display = "none";

      // Ensure user is signed in before calling AI
      let signedIn = false;
      try {{
        const user = await puter.auth.getUser();
        signedIn = user && user.username;
        if (signedIn) {{
          authStatus.innerHTML = "✅ Connecte en tant que <b>" + user.username + "</b>";
        }}
      }} catch(e) {{
        // getUser() threw (401) — not signed in yet
      }}

      if (!signedIn) {{
        try {{
          authStatus.textContent = "Connexion a Puter requise (gratuit)...";
          await puter.auth.signIn();
          const u = await puter.auth.getUser();
          authStatus.innerHTML = "✅ Connecte en tant que <b>" + (u?.username || "") + "</b>";
        }} catch(e) {{
          errorContainer.innerHTML = "Connexion annulee. Vous pouvez utiliser l'option ChatGPT ci-dessous.";
          errorContainer.style.display = "block";
          btn.disabled = false;
          return;
        }}
      }}

      loading.style.display = "block";
      resultContainer.style.display = "none";

      try {{
        const response = await puter.ai.chat(prompt, {{
          model: "google/gemini-3.1-pro-preview"
        }});
        let text;
        if (typeof response === "string") {{
          text = response;
        }} else if (response?.message?.content) {{
          const c = response.message.content;
          text = Array.isArray(c) ? c.map(b => b.text || b).join("") : c;
        }} else {{
          text = JSON.stringify(response);
        }}
        document.getElementById("result-text").innerText = text;
        resultContainer.style.display = "block";
      }} catch(e) {{
        errorContainer.innerHTML = "Erreur : " + e.message +
          "<br><button onclick=\\"location.reload()\\">Reessayer</button>";
        errorContainer.style.display = "block";
        btn.disabled = false;
      }} finally {{
        loading.style.display = "none";
      }}
    }});

    document.getElementById("copy-result-btn").addEventListener("click", async function() {{
      const text = document.getElementById("result-text").innerText;
      try {{
        await navigator.clipboard.writeText(text);
        this.textContent = "✅ Copie !";
        setTimeout(() => this.textContent = "📋 Copier la description", 2000);
      }} catch(e) {{
        this.textContent = "Erreur copie";
      }}
    }});
    </script>
    """,
        height=500,
        scrolling=True,
    )

    # --- Fallback: copy prompt & open ChatGPT ---
    with st.expander("Ou copier le prompt pour ChatGPT"):
        st.components.v1.html(
            f"""
        <button id="copy-btn"
                style="padding:10px 24px;border-radius:8px;border:1px solid #ccc;
                       cursor:pointer;font-size:16px;background:#f0f0f0;">
            📋 Copier le prompt &amp; ouvrir ChatGPT
        </button>
        <script>
        document.getElementById("copy-btn").addEventListener("click", async function() {{
            try {{
                await navigator.clipboard.writeText({_escaped});
                this.textContent = "✅ Copie ! ChatGPT s'ouvre...";
                window.open("https://chatgpt.com", "_blank");
            }} catch(e) {{
                this.textContent = "Erreur: " + e.message;
            }}
        }});
        </script>
        """,
            height=50,
        )
        st.text_area(
            "Prompt (reference)", value=_prompt_text, height=200, disabled=True
        )
