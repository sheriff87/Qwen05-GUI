import os
import json
import csv
import requests
import gradio as gr
from urllib.parse import urlparse
from huggingface_hub import InferenceClient
from gradio_client import Client, handle_file

def terminal_log(message):
    print(f"[V4] {message}", flush=True)

terminal_log("Démarrage de Qwen05-GUI V4...")


# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434"

# ============================================================
# QWEN05-GUI V4 — COST GUARD
# ============================================================
# Le Cost Guard autorise :
# - les modèles Ollama locaux ;
# - les modèles cloud explicitement configurés comme gratuits/quota ;
# - Hugging Face avec son quota/crédit inclus.
#
# Les modèles explicitement payants restent bloqués.
COST_GUARD_MODE = True

# ============================================================
# OPENROUTER
# ============================================================
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_FREE_MODEL = "openrouter/free"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

# ============================================================
# GROQ
# ============================================================
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

# Cost Guard : seuls les modèles explicitement autorisés peuvent être utilisés.
GROQ_ALLOWED_MODELS = {
    "qwen/qwen3.8-27b",
}

GROQ_CODING_MODEL = "qwen/qwen3.8-27b"

# ============================================================
# HUGGING FACE
# ============================================================
HF_TOKEN = (
    os.environ.get("HF_TOKEN")
    or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    or ""
).strip()

HF_IMAGE_ENABLED = True

DEFAULT_MODELS = [
    "qwen5-uncensored:latest",
    "qwen2.5-coder:3b",
]

IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
VIDEO_SPACE = "alexcheng0072/wan27-free-video-generator"
VIDEO_API_NAME = "/generate_video"

TTS_SPACE = "remsky/Kokoro-TTS-Zero"
TTS_API_NAME = "/generate_speech_from_ui"
TTS_DEFAULT_VOICE = "af_sky"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "files", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================
# OLLAMA
# ============================================================

def get_ollama_models():
    try:
        r = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=5
        )
        r.raise_for_status()

        models = [
            m.get("name", "")
            for m in r.json().get("models", [])
        ]

        return [m for m in models if m]

    except Exception:
        return []


def status_text():
    models = get_ollama_models()

    if models:
        return (
            "🟢 **Ollama connecté** — "
            + ", ".join(models)
        )

    return (
        "🔴 **Ollama non disponible** — "
        "vérifie qu'Ollama est lancé."
    )


def refresh_model_choices():
    models = get_ollama_models() or DEFAULT_MODELS

    return (
        gr.Dropdown(
            choices=models,
            value=models[0] if models else None,
            label="Modèle Ollama"
        ),
        status_text()
    )


# ============================================================
# FOURNISSEUR / COST GUARD
# ============================================================

def cost_guard_status():
    """Affiche le mode Cost Guard et les fournisseurs autorisés."""

    if not COST_GUARD_MODE:
        return (
            "🔴 **COST GUARD DÉSACTIVÉ** — "
            "les protections contre les appels payants sont désactivées."
        )

    return (
        "🟢 **COST GUARD ACTIF**\n\n"
        "- 🤖 Ollama : local\n"
        "- ⚡ Groq : uniquement modèles/quota autorisés\n"
        "- ☁️ OpenRouter : uniquement routeur FREE\n"
        "- 🤗 Hugging Face : quota/crédit inclus uniquement\n"
        "- 🔒 Modèles explicitement payants : bloqués"
    )


def openrouter_status():
    if not OPENROUTER_API_KEY:
        return (
            "⚪ **OpenRouter Free non configuré** — "
            "définis `OPENROUTER_API_KEY` pour l'utiliser."
        )
    return (
        "🟢 **OpenRouter Free disponible** — modèle verrouillé sur "
        f"`{OPENROUTER_FREE_MODEL}`."
    )


def normalize_openrouter_history(history):
    messages = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content", "")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content})
    return messages


def openrouter_stream(messages, temperature, top_p, max_tokens):
    """Stream OpenRouter en utilisant uniquement le routeur gratuit."""
    if not COST_GUARD_MODE:
        raise RuntimeError(
            "Le Cost Guard V4 doit être actif pour utiliser OpenRouter FREE."
        )

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY n'est pas configurée. "
            "Aucune requête cloud n'a été envoyée."
        )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:7860",
        "X-Title": "Qwen05-GUI",
    }

    payload = {
        "model": OPENROUTER_FREE_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": float(temperature),
        "top_p": float(top_p),
        "max_tokens": int(max_tokens),
    }

    with requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        stream=True,
        timeout=600,
    ) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            line = raw_line.strip()
            if line.startswith("data: "):
                line = line[6:]
            if line == "[DONE]":
                break
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content") or ""
            if content:
                yield content


# ============================================================
# GROQ
# ============================================================

def groq_stream(messages, temperature, top_p, max_tokens):
    """Stream Groq pour le cloud coding, sous contrôle du Cost Guard."""

    if not COST_GUARD_MODE:
        raise RuntimeError(
            "Le Cost Guard V4 doit être actif pour utiliser Groq."
        )

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY n'est pas configurée. "
            "Aucune requête cloud n'a été envoyée."
        )

    if not GROQ_CODING_MODEL:
        raise RuntimeError(
            "Aucun modèle Groq de coding n'est configuré."
        )

    if GROQ_CODING_MODEL not in GROQ_ALLOWED_MODELS:
        raise RuntimeError(
            f"Modèle Groq bloqué par le Cost Guard : "
            f"{GROQ_CODING_MODEL}"
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_CODING_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": float(temperature),
        "top_p": float(top_p),
        "max_tokens": int(max_tokens),
    }

    with requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        stream=True,
        timeout=600,
    ) as response:
        response.raise_for_status()

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue

            line = raw_line.strip()

            if line.startswith("data: "):
                line = line[6:]

            if line == "[DONE]":
                break

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            choices = data.get("choices") or []

            if not choices:
                continue

            delta = choices[0].get("delta") or {}
            content = delta.get("content") or ""

            if content:
                yield content


# ============================================================
# CHAT
# ============================================================

def clear_chat():
    return [], ""


# ============================================================
# FICHIERS
# ============================================================

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".htm",
    ".css",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".ps1",
    ".bat",
    ".cmd",
    ".sh",
    ".sql",
    ".ini",
    ".cfg",
    ".conf",
    ".log",
    ".csv",
}


def get_file_path(file_obj):
    """
    Gradio peut fournir différents types d'objet
    selon la version/configuration.
    """

    if file_obj is None:
        return None

    if isinstance(file_obj, str):
        return file_obj

    if hasattr(file_obj, "name"):
        return file_obj.name

    if isinstance(file_obj, dict):
        return file_obj.get("path") or file_obj.get("name")

    return None


def describe_files(files):
    """
    Affiche la liste des fichiers chargés.
    """

    if not files:
        return "Aucun fichier chargé."

    lines = ["### 📎 Fichiers sélectionnés"]

    for f in files:
        path = get_file_path(f)

        if path:
            name = os.path.basename(path)
            size = os.path.getsize(path)

            if size < 1024:
                size_text = f"{size} octets"
            elif size < 1024 * 1024:
                size_text = f"{size / 1024:.1f} Ko"
            else:
                size_text = f"{size / (1024 * 1024):.1f} Mo"

            lines.append(
                f"- 📄 **{name}** — {size_text}"
            )

    return "\n".join(lines)


def read_text_file(path):
    """
    Lecture robuste des fichiers texte.
    """

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin-1",
    ]

    for encoding in encodings:
        try:
            with open(
                path,
                "r",
                encoding=encoding,
                errors="strict"
            ) as f:
                return f.read()

        except UnicodeDecodeError:
            continue

    with open(
        path,
        "r",
        encoding="utf-8",
        errors="replace"
    ) as f:
        return f.read()


def build_file_context(files):
    """
    Transforme les fichiers texte en contexte
    utilisable par le LLM.
    """

    if not files:
        return ""

    sections = []

    for f in files:
        path = get_file_path(f)

        if not path or not os.path.exists(path):
            continue

        filename = os.path.basename(path)
        extension = os.path.splitext(filename)[1].lower()

        if extension not in TEXT_EXTENSIONS:
            sections.append(
                f"[FICHIER NON-TEXTE : {filename}]\n"
                "Ce fichier est chargé mais son contenu "
                "n'est pas encore transmis au modèle."
            )
            continue

        try:
            content = read_text_file(path)

            # Protection contre les fichiers énormes
            max_chars = 100000

            if len(content) > max_chars:
                content = (
                    content[:max_chars]
                    + "\n\n[CONTENU TRONQUÉ]"
                )

            sections.append(
                f"===== {filename} =====\n"
                f"{content}\n"
                f"===== FIN {filename} ====="
            )

        except Exception as e:
            sections.append(
                f"[ERREUR LECTURE {filename}]\n{e}"
            )

    if not sections:
        return ""

    return (
        "\n\n"
        "===== FICHIERS FOURNIS =====\n"
        + "\n\n".join(sections)
        + "\n===== FIN DES FICHIERS =====\n"
    )


def clear_files():
    return [], "Aucun fichier chargé."


# ============================================================
# CHAT AVEC FICHIERS
# ============================================================

def chat_stream(
    message,
    history,
    source,
    model,
    temperature,
    top_p,
    max_tokens,
    files
):
    terminal_log(f"Chat → {source}")
    message = (message or "").strip()
    history = list(history or [])
    files = files or []

    if not message:
        yield history
        return

    file_context = build_file_context(files)
    final_user_message = message
    if file_context:
        final_user_message = message + "\n\n" + file_context

    # --------------------------------------------------------
    # HISTORIQUE
    # --------------------------------------------------------
    messages = normalize_openrouter_history(history)
    messages.append({"role": "user", "content": final_user_message})

    # --------------------------------------------------------
    # AFFICHAGE
    # --------------------------------------------------------
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    yield history

    try:
        if source == "🤖 Ollama local":
            if not model:
                history[-1]["content"] = "❌ Aucun modèle Ollama sélectionné."
                yield history
                return

            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": float(temperature),
                    "top_p": float(top_p),
                    "num_predict": int(max_tokens)
                }
            }

            with requests.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                stream=True,
                timeout=600
            ) as response:
                response.raise_for_status()
                answer = ""
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    data = json.loads(line)
                    answer += (
                        data.get("message", {}).get("content", "")
                    )
                    history[-1]["content"] = answer
                    yield history
                    if data.get("done"):
                        break
            return

        if source == "☁️ OpenRouter — FREE":
            answer = ""
            for chunk in openrouter_stream(
                messages, temperature, top_p, max_tokens
            ):
                answer += chunk
                history[-1]["content"] = answer
                yield history
            return

        if source == "⚡ Groq — Coding":
            answer = ""
            for chunk in groq_stream(
                messages, temperature, top_p, max_tokens
            ):
                answer += chunk
                history[-1]["content"] = answer
                yield history
            return

        history[-1]["content"] = "âŒ Source IA inconnue."
        yield history

    except requests.exceptions.ConnectionError:
        if source == "🤖 Ollama local":
            provider = "Ollama"
            target = "http://127.0.0.1:11434"
        elif source == "⚡ Groq — Coding":
            provider = "Groq"
            target = "https://api.groq.com"
        elif source == "☁️ OpenRouter — FREE":
            provider = "OpenRouter"
            target = "https://openrouter.ai"
        else:
            provider = "fournisseur cloud"
            target = "service distant"

        history[-1]["content"] = (
            f"❌ Impossible de joindre {provider}.\n\n"
            f"Cible : {target}\n\n"
            "Vérifie la connexion et la configuration de ce fournisseur."
        )
        yield history
    except requests.exceptions.HTTPError as e:
        details = ""
        try:
            details = response.text[:1000]
        except Exception:
            pass
        history[-1]["content"] = (
            f"❌ Erreur HTTP : {e}\n\n{details}"
        )
        yield history

    except Exception as e:
        history[-1]["content"] = f"❌ Erreur : {e}"
        yield history


# ============================================================
# IMAGE HUGGING FACE
# ============================================================

def generate_audio(text, voice_name="af_sky", speed=1.0):
    terminal_log("Audio → Hugging Face ZeroGPU / Kokoro")

    if not COST_GUARD_MODE:
        terminal_log("Audio bloqué : Cost Guard désactivé.")
        return None, "🔒 Génération audio bloquée : Cost Guard désactivé."

    text = (text or "").strip()
    if not text:
        terminal_log("Audio bloqué : texte vide.")
        return None, "⚠️ Saisis un texte."

    try:
        client = Client(TTS_SPACE)

        result = client.predict(
            text,
            voice_name,
            float(speed),
            api_name=TTS_API_NAME
        )

        audio_path = result[0] if isinstance(result, tuple) else result

        if not audio_path:
            raise RuntimeError("Le Space n'a retourné aucun fichier audio.")

        filename = os.path.join(BASE_DIR, "generated_audio.wav")

        import shutil
        shutil.copy2(audio_path, filename)

        terminal_log(
            f"Audio généré avec succès | voix={voice_name} | vitesse={speed}"
        )
        terminal_log(f"Fichier audio : {filename}")

        return (
            filename,
            "🟢 Audio généré avec succès via Hugging Face ZeroGPU / Kokoro."
        )

    except Exception as e:
        terminal_log(f"Erreur audio : {e}")
        return None, f"🔴 Génération audio : {e}"


def generate_video(input_image, prompt, aspect_ratio="832x480", duration_seconds=2):
    terminal_log("Vidéo → Hugging Face ZeroGPU / Wan")

    if not COST_GUARD_MODE:
        terminal_log("Vidéo bloquée : Cost Guard désactivé.")
        return None, "🔒 Génération vidéo bloquée : Cost Guard désactivé."

    if input_image is None:
        terminal_log("Vidéo bloquée : aucune image.")
        return None, "⚠️ Sélectionne une image."

    prompt = (prompt or "").strip()
    if not prompt:
        terminal_log("Vidéo bloquée : prompt vide.")
        return None, "⚠️ Décris le mouvement ou la scène."

    try:
        terminal_log(
            f"Vidéo → Space={VIDEO_SPACE} | format={aspect_ratio} | durée={duration_seconds}s"
        )

        client = Client(VIDEO_SPACE)

        result = client.predict(
            handle_file(input_image),
            prompt,
            aspect_ratio,
            int(duration_seconds),
            api_name=VIDEO_API_NAME
        )

        video_info, seed = result

        if isinstance(video_info, dict):
            video_path = video_info.get("video")
        else:
            video_path = video_info

        if not video_path:
            raise RuntimeError("Le Space n'a retourné aucun fichier vidéo.")

        filename = os.path.join(BASE_DIR, "generated_video.mp4")

        import shutil
        shutil.copy2(video_path, filename)

        terminal_log(f"Vidéo générée avec succès | seed={seed}")
        terminal_log(f"Fichier vidéo : {filename}")

        return filename, f"🟢 Vidéo générée avec succès — seed {seed}"

    except Exception as e:
        terminal_log(f"Erreur vidéo : {e}")
        return None, f"🔴 Génération vidéo : {e}"


def generate_image(prompt):
    terminal_log("Image → Hugging Face")

    if not HF_IMAGE_ENABLED:
        return (
            None,
            "🔒 Génération d'image Hugging Face désactivée par le Cost Guard."
        )

    prompt = (prompt or "").strip()

    if not prompt:

        return (
            None,
            "⚠️ Décris l'image à générer."
        )

    try:

        token = HF_TOKEN

        if not token:
            return (
                None,
                "⚠️ Hugging Face n'est pas configuré : "
                "définis HF_TOKEN ou HUGGINGFACEHUB_API_TOKEN."
            )

        client = InferenceClient(token=token)

        image = client.text_to_image(
            prompt=prompt,
            model=IMAGE_MODEL
        )

        filename = os.path.join(
            BASE_DIR,
            "generated_image.png"
        )

        image.save(filename)

        return (
            filename,
            "🟡 Image générée via Hugging Face. Vérifie le quota/coût "
            "du provider avant utilisation : la V4 ne considère pas HF "
            "comme du gratuit illimité."
        )

    except Exception as e:

        return (
            None,
            f"🔴 Hugging Face : {e}"
        )


# ============================================================
# INTERFACE
# ============================================================

with gr.Blocks(
    title="Qwen05-GUI V4 — Gratuit"
) as demo:

    gr.Markdown(
        "# 🤖 Qwen05-GUI V4 — Assistant IA\n"
        "🟢 Mode GRATUIT uniquement · Ollama + OpenRouter Free + fichiers"
    )

    # --------------------------------------------------------
    # ZONE PRINCIPALE
    # --------------------------------------------------------

    with gr.Row():

        with gr.Column(scale=3):

            source = gr.Radio(
                [
                    "🤖 Ollama local",
                    "⚡ Groq — Coding",
                    "☁️ OpenRouter — FREE"
                ],
                value="🤖 Ollama local",
                label="Source / relais — V4 COST GUARD"
            )

            current_models = (
                get_ollama_models()
                or DEFAULT_MODELS
            )

            model = gr.Dropdown(
                choices=current_models,
                value=current_models[0],
                label="Modèle Ollama"
            )

            status = gr.Markdown(
                status_text()
            )

            gr.Markdown(cost_guard_status())
            openrouter_status_box = gr.Markdown(openrouter_status())

            chatbot = gr.Chatbot(
                label="Conversation",
                height=500,
                layout="bubble",
                render_markdown=True
            )

            message = gr.Textbox(
                label="Message",
                placeholder=(
                    "Écris ton message ici..."
                ),
                lines=3
            )

            # ------------------------------------------------
            # FICHIERS
            # ------------------------------------------------

            gr.Markdown("### 📎 Fichiers")

            files = gr.File(
                label=(
                    "Ajoute des fichiers "
                    "(ou glisse-dépose ici)"
                ),
                file_count="multiple",
                type="filepath"
            )

            file_status = gr.Markdown(
                "Aucun fichier chargé."
            )

            clear_files_button = gr.Button(
                "🗑️ Retirer les fichiers"
            )

            # ------------------------------------------------
            # BOUTONS
            # ------------------------------------------------

            with gr.Row():

                send = gr.Button(
                    "➤ Envoyer",
                    variant="primary"
                )

                new_button = gr.Button(
                    "＋ Nouvelle discussion"
                )

        # ----------------------------------------------------
        # PARAMÈTRES
        # ----------------------------------------------------

        with gr.Column(scale=1):

            gr.Markdown(
                "### ⚙️ Paramètres"
            )

            temperature = gr.Slider(
                minimum=0,
                maximum=1.5,
                value=0.7,
                step=0.1,
                label="Température"
            )

            top_p = gr.Slider(
                minimum=0,
                maximum=1,
                value=0.9,
                step=0.05,
                label="Top P"
            )

            max_tokens = gr.Slider(
                minimum=256,
                maximum=4096,
                value=2048,
                step=256,
                label="Max tokens"
            )

            refresh = gr.Button(
                "🔄 Actualiser les modèles"
            )

    # ========================================================
    # ONGLET DIAGNOSTIC / COST GUARD
    # ========================================================
    with gr.Tab("🛡️ Cost Guard / Diagnostic"):
        gr.Markdown(
            "## 🛡️ Qwen05-GUI V4 — Cost Guard\n"
            "Cette version applique une liste blanche stricte des fournisseurs et modèles autorisés.\n\n"
            "- 🤖 Ollama : local, aucune API cloud\n"
            "- ⚡ Groq : `qwen/qwen3.8-27b` uniquement\n"
            "- ☁️ OpenRouter : `openrouter/free` uniquement\n"
            "- 🤗 Hugging Face : multimédia uniquement, avec quota/crédit contrôlé\n"
            "- 🔒 Modèles non autorisés : bloqués par le Cost Guard\n"
            "- 💳 Aucun modèle explicitement payant autorisé par V4"
        )
        gr.Markdown(cost_guard_status())
        gr.Markdown(
            "### ⚡ Groq — Coding\n"
            f"Modèle autorisé : `{GROQ_CODING_MODEL}`\n\n"
            "Whitelist Cost Guard : `qwen/qwen3.8-27b` uniquement."
        )
        gr.Markdown(openrouter_status())
        gr.Markdown(
            "### 🔑 Clés API\n"
            "Les clés ne sont pas écrites dans le programme. Elles sont "
            "fournies par les variables d'environnement `GROQ_API_KEY` et "
            "`OPENROUTER_API_KEY`."
        )

    # ========================================================
    # ONGLET IMAGE
    # ========================================================

    with gr.Tab(
        "🎨 Génération d'image"
    ):

        image_prompt = gr.Textbox(
            label="Description de l'image",
            placeholder=(
                "Exemple : une ville futuriste "
                "au coucher du soleil, très détaillée..."
            ),
            lines=4
        )

        image_button = gr.Button(
            "🖼️ Générer l'image",
            variant="primary"
        )

        image_output = gr.Image(
            label="Résultat",
            type="filepath"
        )

        image_status = gr.Markdown()

    # ========================================================
    # ONGLET VIDEO
    # ========================================================

    with gr.Tab(
        "🎬 Génération vidéo"
    ):

        video_image = gr.Image(
            label="Image de départ",
            type="filepath"
        )

        video_prompt = gr.Textbox(
            label="Description du mouvement",
            placeholder=(
                "Exemple : la caméra avance doucement, "
                "les cheveux bougent avec le vent..."
            ),
            lines=4
        )

        with gr.Row():
            video_aspect = gr.Dropdown(
                choices=[
                    "832x480",
                    "480x832",
                    "640x640"
                ],
                value="832x480",
                label="Format"
            )

            video_duration = gr.Dropdown(
                choices=[2, 3, 4, 5],
                value=2,
                label="Durée (secondes)"
            )

        video_button = gr.Button(
            "🎬 Générer la vidéo",
            variant="primary"
        )

        video_output = gr.Video(
            label="Vidéo générée"
        )

        video_status = gr.Markdown(
            "🟢 Génération vidéo via Hugging Face ZeroGPU."
        )


    # ========================================================
    # ONGLET AUDIO
    # ========================================================

    with gr.Tab(
        "🔊 Génération audio"
    ):

        audio_text = gr.Textbox(
            label="Texte à vocaliser",
            placeholder="Écris le texte que Kokoro doit prononcer...",
            lines=6
        )

        with gr.Row():
            audio_voice = gr.Dropdown(
                choices=["af_sky"],
                value="af_sky",
                label="Voix"
            )

            audio_speed = gr.Slider(
                minimum=0.5,
                maximum=2.0,
                value=1.0,
                step=0.05,
                label="Vitesse"
            )

        audio_button = gr.Button(
            "🔊 Générer l'audio",
            variant="primary"
        )

        audio_output = gr.Audio(
            label="Audio généré",
            type="filepath"
        )

        audio_status = gr.Markdown(
            "🟢 Kokoro via Hugging Face ZeroGPU."
        )

    # ========================================================
    # ÉVÉNEMENTS
    # ========================================================

    audio_button.click(
        generate_audio,
        inputs=[
            audio_text,
            audio_voice,
            audio_speed
        ],
        outputs=[
            audio_output,
            audio_status
        ]
    )



    refresh.click(
        refresh_model_choices,
        outputs=[
            model,
            status
        ]
    )

    new_button.click(
        clear_chat,
        outputs=[
            chatbot,
            message
        ]
    )

    files.change(
        describe_files,
        inputs=files,
        outputs=file_status
    )

    clear_files_button.click(
        clear_files,
        outputs=[
            files,
            file_status
        ]
    )

    send.click(
        chat_stream,
        inputs=[
            message,
            chatbot,
            source,
            model,
            temperature,
            top_p,
            max_tokens,
            files
        ],
        outputs=chatbot
    ).then(
        lambda: "",
        outputs=message
    )

    message.submit(
        chat_stream,
        inputs=[
            message,
            chatbot,
            source,
            model,
            temperature,
            top_p,
            max_tokens,
            files
        ],
        outputs=chatbot
    ).then(
        lambda: "",
        outputs=message
    )

    image_button.click(
        generate_image,
        inputs=image_prompt,
        outputs=[
            image_output,
            image_status
        ]
    )

    video_button.click(
        generate_video,
        inputs=[
            video_image,
            video_prompt,
            video_aspect,
            video_duration
        ],
        outputs=[
            video_output,
            video_status
        ]
    )


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True
    )
