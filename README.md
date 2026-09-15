# Qwen05-GUI

<p align="center">
  <strong>Local & Cloud AI Assistant GUI</strong>
</p>

<p align="center">
  A desktop-friendly AI interface powered by Ollama, Qwen, Groq, OpenRouter and Hugging Face.
</p>

<p align="center">
  <img src="assets/qwen-gui-main0.PNG" alt="Qwen05-GUI main interface" width="900">
</p>

<p align="center">
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://www.gradio.app/">
    <img src="https://img.shields.io/badge/Gradio-6.27-orange" alt="Gradio">
  </a>
  <a href="https://ollama.com/">
    <img src="https://img.shields.io/badge/Ollama-Local_AI-black" alt="Ollama">
  </a>
  <a href="https://github.com/sheriff87/Qwen05-GUI">
    <img src="https://img.shields.io/github/stars/sheriff87/Qwen05-GUI?style=flat&logo=github" alt="GitHub Stars">
  </a>
</p>

---

## ✨ Overview

**Qwen05-GUI** is a local-first AI assistant interface designed to bring multiple AI capabilities together in a simple Gradio application.

The project combines **local AI models** running through Ollama with selected **cloud AI services**, while keeping provider configuration and potential costs under control.

### What it provides

- 💬 AI conversations
- 🧠 Local Qwen models
- 💻 Coding assistance
- ☁️ Cloud AI providers
- 🎨 Image generation
- 📁 Multi-format file analysis
- ⚡ Streaming responses
- ⚙️ Generation parameters
- 🛡️ Cost-aware cloud usage

---

## 📸 Screenshots

<p align="center">
  <img src="assets/qwen-gui-main0.PNG" alt="Qwen05-GUI main interface" width="48%">
  <img src="assets/qwen-gui-main1.PNG" alt="Qwen05-GUI interface" width="48%">
</p>

<p align="center">
  <img src="assets/qwen-gui-main2.PNG" alt="Qwen05-GUI features" width="48%">
  <img src="assets/qwen-gui-main3.PNG" alt="Qwen05-GUI media capabilities" width="48%">
</p>

---

## 🚀 Features

### 🧠 Local AI — Ollama

Run AI models locally on your own computer through Ollama.

Benefits:

- Local inference
- No cloud API required for local models
- Greater privacy
- Offline use for supported features
- Easy model switching

Example models include:

- Qwen
- Qwen Coder
- Other models supported by Ollama

---

### 💻 Coding Assistant

Qwen Coder can be used for programming-related tasks such as:

- Python
- JavaScript
- HTML
- CSS
- JSON
- YAML
- PowerShell
- Batch
- SQL
- Configuration files

Loaded source files can also be sent directly to the AI for analysis.

---

### ☁️ Cloud AI

Qwen05-GUI can connect to cloud providers when an API key is configured.

Supported integrations include:

- Groq
- OpenRouter
- Hugging Face

Cloud services are kept separate from local Ollama models.

---

### 🎨 Hugging Face

Hugging Face is integrated for supported AI media capabilities, including image generation.

Example model:

```text
black-forest-labs/FLUX.1-schnell
