# 🎬 AI Multi-Speaker Video Dubbing Studio (100% Free & Local)

A modern, production-grade web application for automatic AI video dubbing with **Multi-Speaker Diarization** (detecting multiple speakers and assigning distinct neural voices to each speaker).

Built with **100% free and open-source tools**:
- **Transcription**: [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI Whisper via CTranslate2 — up to 4x faster and lower memory footprint)
- **Speaker Diarization**: [pyannote.audio](https://github.com/pyannote/pyannote-audio) 3.1 (with built-in acoustic clustering fallback for zero-setup execution)
- **Translation**: [deep-translator](https://github.com/nidhaloff/deep-translator) (Google Translate free wrapper — no API keys required)
- **Multi-Voice Text-to-Speech**: [edge-tts](https://github.com/rany2/edge-tts) (Microsoft Edge High-Quality Neural Voices)
- **Audio/Video Processing & Sync**: [FFmpeg](https://ffmpeg.org/) (audio extraction, time-stretching via `atempo`, and stream-copy video remuxing)
- **Backend**: FastAPI + Uvicorn + Server-Sent Events (SSE)
- **Frontend**: Responsive Tailwind CSS + HTML5 Video Player + Real-Time Terminal Log & Diarization Inspector

---

## 📁 Project Directory Structure

```
ai-video-dubbing/
├── app.py                  # FastAPI server & async task coordinator
├── dubbing_engine.py       # Core pipeline (Extract -> Whisper -> Diarize -> Translate -> TTS -> Sync -> Remux)
├── voices.py               # Microsoft Edge Neural Voice mappings for multiple languages
├── requirements.txt        # Python dependency manifest
├── static/
│   ├── index.html          # Web UI with glassmorphic cards, upload dropzone & video players
│   ├── app.js              # Frontend logic (drag & drop, live SSE progress streaming, transcript cards)
│   └── style.css           # Custom scrollbars and styling
├── uploads/                # Temporary directory for uploaded videos (auto-created)
├── outputs/                # Directory where final dubbed videos are saved (auto-created)
└── README.md               # Step-by-step setup and usage guide
```

---

## 🛠️ Prerequisites

Before running the server, ensure you have the following installed:

### 1. Python 3.10+
Check with:
```bash
python --version
```

### 2. FFmpeg & FFprobe
FFmpeg is required for audio extraction, time-stretching, and video remuxing.

- **Windows**:
  Run PowerShell as Administrator:
  ```powershell
  winget install Gyan.FFmpeg
  ```
  *(Or download from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) and add the `bin` folder to your system PATH).*
- **macOS**:
  ```bash
  brew install ffmpeg
  ```
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```

Verify FFmpeg is available in your terminal:
```bash
ffmpeg -version
ffprobe -version
```

---

## 🚀 Step-by-Step Installation

### Step 1: Clone or Open the Project
Open a terminal in the project directory:
```bash
cd C:\Users\NUKE\.gemini\antigravity\scratch\ai-video-dubbing
```

### Step 2: Create and Activate a Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install PyTorch
- **If you have an NVIDIA GPU (CUDA support)**:
  ```bash
  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
  ```
- **If you are using CPU only**:
  ```bash
  pip install torch torchaudio
  ```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🔑 Speaker Diarization Setup (Pyannote vs. Acoustic Fallback)

This application supports **two modes** for speaker diarization:

1. **Built-in Acoustic Fallback (Default - 0 Setup Required)**:
   - If you do not enter a Hugging Face token, the app automatically extracts MFCC and spectral acoustic features from each segment and clusters speakers using KMeans.
   - **Requires no account or setup! Works right out of the box.**

2. **Official Pyannote 3.1 (Recommended for maximum accuracy)**:
   - Pyannote provides industry-leading diarization. To use it for free:
     1. Create a free account at [huggingface.co](https://huggingface.co/).
     2. Accept user conditions for [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) and [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0).
     3. Go to [Settings -> Access Tokens](https://huggingface.co/settings/tokens) and create a read token (`hf_...`).
     4. Enter the token in the **Advanced AI Models** accordion in the web UI.

---

## ▶️ Running the Application

Start the FastAPI server:

```bash
python app.py
```
*(Or via Uvicorn directly: `uvicorn app:app --host 0.0.0.0 --port 8000 --reload`)*

Once started, open your web browser and navigate to:
👉 **http://localhost:8000**

---

## 💡 How the Audio-Video Sync Works

A common issue in AI video dubbing is audio drift (e.g., translated Spanish sentences are often ~20% longer than original English sentences).

This project solves audio sync through a multi-stage pipeline:
1. **Timestamp Extraction**: Whisper extracts exact start and end timestamps for each dialogue segment (`target_duration = end - start`).
2. **Dynamic Time-Stretching**: After Edge-TTS generates neural audio, FFmpeg's `atempo` filter adjusts the playback rate to match the segment duration without changing vocal pitch.
3. **Master Audio Buffering**: Each dialogue chunk is placed onto an exact sample-accurate master audio timeline using NumPy. Pauses and natural speech spacing are preserved.
4. **Fast Remuxing**: FFmpeg replaces or ducks the original audio track while keeping the video stream intact (`-c:v copy`), completing rendering in seconds.

---

## 🌐 Supported Languages & Voices

Supports automatic voice allocation (cycling between Male and Female neural voices per speaker):
- 🇮🇳 **Hindi (`hi`)**: `hi-IN-MadhurNeural` (M), `hi-IN-SwaraNeural` (F)
- 🇵🇰 **Urdu (`ur`)**: `ur-PK-AsadNeural` (M), `ur-PK-UzmaNeural` (F)
- 🇺🇸 **English (`en`)**: `en-US-GuyNeural` (M), `en-US-JennyNeural` (F), `en-US-ChristopherNeural` (M), `en-US-AriaNeural` (F)
- 🇪🇸 **Spanish (`es`)**: `es-ES-AlvaroNeural` (M), `es-ES-ElviraNeural` (F)
- 🇫🇷 **French (`fr`)**: `fr-FR-HenriNeural` (M), `fr-FR-DeniseNeural` (F)
- 🇩🇪 **German (`de`)**: `de-DE-ConradNeural` (M), `de-DE-KatjaNeural` (F)
- 🇸🇦 **Arabic (`ar`)**: `ar-SA-HamedNeural` (M), `ar-SA-ZariyahNeural` (F)
- 🇯🇵 **Japanese (`ja`)**: `ja-JP-KeitaNeural` (M), `ja-JP-NanamiNeural` (F)
- 🇧🇷 **Portuguese (`pt`)**: `pt-BR-AntonioNeural` (M), `pt-BR-FranciscaNeural` (F)
- 🇷🇺 **Russian (`ru`)**: `ru-RU-DmitryNeural` (M), `ru-RU-SvetlanaNeural` (F)
- 🇨🇳 **Chinese (`zh-CN`)**: `zh-CN-YunxiNeural` (M), `zh-CN-XiaoxiaoNeural` (F)
- And more! Add additional voices easily in [voices.py](voices.py).
