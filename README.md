Qwen05-GUI

Interface graphique locale et cloud pour travailler avec des modèles d'intelligence artificielle.

Qwen05-GUI combine des modèles locaux via Ollama avec des services cloud optionnels.

Fonctionnalités

- Modèles locaux avec Ollama
- Modèle de coding via Groq
- Intégration Hugging Face
- Chargement de fichiers
- Support de fichiers texte et code
- Streaming des réponses
- Paramètres de génération
- Contrôle des coûts cloud

Prérequis

- Windows 10 ou supérieur
- Python 3.10
- Ollama

Installation

Créer l'environnement Python :

py -3.10 -m venv .venv

Installer les dépendances :

python -m pip install -r requirements.txt

Lancement

Lancer l'application :

py -3.10 -X faulthandler gradio_app_V4.py

L'interface est disponible à :

http://127.0.0.1:7860

Configuration

Les clés API sont fournies via des variables d'environnement.

Variables utilisées :

OPENROUTER_API_KEY=
GROQ_API_KEY=
HF_TOKEN=
OLLAMA_URL=http://127.0.0.1:11434

Ne publiez jamais vos véritables clés API sur GitHub.

Vous pouvez utiliser ".env.example" comme modèle de configuration.

Sécurité

Les fichiers ".env", les logs, les fichiers temporaires, les médias générés et les sauvegardes locales sont exclus du dépôt Git.

Les clés API doivent rester privées.

Architecture

Local

Ollama permet d'utiliser les modèles IA directement sur l'ordinateur.

Cloud

Les intégrations cloud sont optionnelles et peuvent être utilisées selon les besoins :

- Groq
- OpenRouter
- Hugging Face

Le projet est conçu pour séparer les modèles locaux des services cloud.

État du projet

Version actuelle : V4

Le projet est actuellement en développement.

Licence

Licence open source à définir.