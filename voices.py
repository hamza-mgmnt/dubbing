"""
Edge-TTS Voice mapping for multi-speaker video dubbing.
Provides free high-quality Microsoft Edge Neural TTS voices across multiple languages,
with alternating male/female voices per speaker ID.
"""

# Preset voices per language: alternating [Male, Female, Male, Female, ...]
LANGUAGE_VOICES = {
    "hi": {
        "name": "Hindi (हिंदी)",
        "flag": "🇮🇳",
        "voices": [
            {"id": "hi-IN-MadhurNeural", "gender": "Male", "label": "Madhur (Male)"},
            {"id": "hi-IN-SwaraNeural", "gender": "Female", "label": "Swara (Female)"},
        ]
    },
    "ur": {
        "name": "Urdu (اردو)",
        "flag": "🇵🇰",
        "voices": [
            {"id": "ur-PK-AsadNeural", "gender": "Male", "label": "Asad (Male)"},
            {"id": "ur-PK-UzmaNeural", "gender": "Female", "label": "Uzma (Female)"},
            {"id": "ur-IN-SalmanNeural", "gender": "Male", "label": "Salman (Male)"},
            {"id": "ur-IN-GulNeural", "gender": "Female", "label": "Gul (Female)"},
        ]
    },
    "en": {
        "name": "English (US)",
        "flag": "🇺🇸",
        "voices": [
            {"id": "en-US-GuyNeural", "gender": "Male", "label": "Guy (Male)"},
            {"id": "en-US-JennyNeural", "gender": "Female", "label": "Jenny (Female)"},
            {"id": "en-US-ChristopherNeural", "gender": "Male", "label": "Christopher (Male)"},
            {"id": "en-US-AriaNeural", "gender": "Female", "label": "Aria (Female)"},
            {"id": "en-US-EricNeural", "gender": "Male", "label": "Eric (Male)"},
            {"id": "en-US-MichelleNeural", "gender": "Female", "label": "Michelle (Female)"},
        ]
    },
    "es": {
        "name": "Spanish (Español)",
        "flag": "🇪🇸",
        "voices": [
            {"id": "es-ES-AlvaroNeural", "gender": "Male", "label": "Alvaro (Male)"},
            {"id": "es-ES-ElviraNeural", "gender": "Female", "label": "Elvira (Female)"},
            {"id": "es-MX-JorgeNeural", "gender": "Male", "label": "Jorge (Male)"},
            {"id": "es-MX-DaliaNeural", "gender": "Female", "label": "Dalia (Female)"},
        ]
    },
    "fr": {
        "name": "French (Français)",
        "flag": "🇫🇷",
        "voices": [
            {"id": "fr-FR-HenriNeural", "gender": "Male", "label": "Henri (Male)"},
            {"id": "fr-FR-DeniseNeural", "gender": "Female", "label": "Denise (Female)"},
            {"id": "fr-FR-AlainNeural", "gender": "Male", "label": "Alain (Male)"},
            {"id": "fr-FR-BrigitteNeural", "gender": "Female", "label": "Brigitte (Female)"},
        ]
    },
    "de": {
        "name": "German (Deutsch)",
        "flag": "🇩🇪",
        "voices": [
            {"id": "de-DE-ConradNeural", "gender": "Male", "label": "Conrad (Male)"},
            {"id": "de-DE-KatjaNeural", "gender": "Female", "label": "Katja (Female)"},
            {"id": "de-DE-KillianNeural", "gender": "Male", "label": "Killian (Male)"},
            {"id": "de-DE-AmalaNeural", "gender": "Female", "label": "Amala (Female)"},
        ]
    },
    "ar": {
        "name": "Arabic (العربية)",
        "flag": "🇸🇦",
        "voices": [
            {"id": "ar-SA-HamedNeural", "gender": "Male", "label": "Hamed (Male)"},
            {"id": "ar-SA-ZariyahNeural", "gender": "Female", "label": "Zariyah (Female)"},
            {"id": "ar-EG-ShakirNeural", "gender": "Male", "label": "Shakir (Male)"},
            {"id": "ar-EG-SalmaNeural", "gender": "Female", "label": "Salma (Female)"},
        ]
    },
    "ja": {
        "name": "Japanese (日本語)",
        "flag": "🇯🇵",
        "voices": [
            {"id": "ja-JP-KeitaNeural", "gender": "Male", "label": "Keita (Male)"},
            {"id": "ja-JP-NanamiNeural", "gender": "Female", "label": "Nanami (Female)"},
            {"id": "ja-JP-NaokiNeural", "gender": "Male", "label": "Naoki (Male)"},
            {"id": "ja-JP-AoiNeural", "gender": "Female", "label": "Aoi (Female)"},
        ]
    },
    "pt": {
        "name": "Portuguese (Português)",
        "flag": "🇧🇷",
        "voices": [
            {"id": "pt-BR-AntonioNeural", "gender": "Male", "label": "Antonio (Male)"},
            {"id": "pt-BR-FranciscaNeural", "gender": "Female", "label": "Francisca (Female)"},
            {"id": "pt-PT-DuarteNeural", "gender": "Male", "label": "Duarte (Male)"},
            {"id": "pt-PT-RaquelNeural", "gender": "Female", "label": "Raquel (Female)"},
        ]
    },
    "ru": {
        "name": "Russian (Русский)",
        "flag": "🇷🇺",
        "voices": [
            {"id": "ru-RU-DmitryNeural", "gender": "Male", "label": "Dmitry (Male)"},
            {"id": "ru-RU-SvetlanaNeural", "gender": "Female", "label": "Svetlana (Female)"},
        ]
    },
    "it": {
        "name": "Italian (Italiano)",
        "flag": "🇮🇹",
        "voices": [
            {"id": "it-IT-DiegoNeural", "gender": "Male", "label": "Diego (Male)"},
            {"id": "it-IT-ElsaNeural", "gender": "Female", "label": "Elsa (Female)"},
            {"id": "it-IT-IsabellaNeural", "gender": "Female", "label": "Isabella (Female)"},
        ]
    },
    "tr": {
        "name": "Turkish (Türkçe)",
        "flag": "🇹🇷",
        "voices": [
            {"id": "tr-TR-AhmetNeural", "gender": "Male", "label": "Ahmet (Male)"},
            {"id": "tr-TR-EmelNeural", "gender": "Female", "label": "Emel (Female)"},
        ]
    },
    "bn": {
        "name": "Bengali (বাংলা)",
        "flag": "🇧🇩",
        "voices": [
            {"id": "bn-BD-PradeepNeural", "gender": "Male", "label": "Pradeep (Male)"},
            {"id": "bn-BD-NabanitaNeural", "gender": "Female", "label": "Nabanita (Female)"},
            {"id": "bn-IN-BashkarNeural", "gender": "Male", "label": "Bashkar (Male)"},
            {"id": "bn-IN-TanishaaNeural", "gender": "Female", "label": "Tanishaa (Female)"},
        ]
    },
    "zh-CN": {
        "name": "Chinese (Mandarin / 普通话)",
        "flag": "🇨🇳",
        "voices": [
            {"id": "zh-CN-YunxiNeural", "gender": "Male", "label": "Yunxi (Male)"},
            {"id": "zh-CN-XiaoxiaoNeural", "gender": "Female", "label": "Xiaoxiao (Female)"},
            {"id": "zh-CN-YunjianNeural", "gender": "Male", "label": "Yunjian (Male)"},
            {"id": "zh-CN-XiaoyiNeural", "gender": "Female", "label": "Xiaoyi (Female)"},
        ]
    }
}

def get_voice_for_speaker(language: str, speaker_index: int) -> dict:
    """
    Assigns a distinct neural voice to a speaker based on their index.
    Cycles through available voices for the language.
    """
    lang_info = LANGUAGE_VOICES.get(language, LANGUAGE_VOICES["en"])
    voices = lang_info["voices"]
    assigned = voices[speaker_index % len(voices)]
    return assigned

def get_supported_languages() -> list:
    """Returns a list of supported languages for API/frontend dropdown."""
    return [
        {"code": code, "name": data["name"], "flag": data["flag"]}
        for code, data in LANGUAGE_VOICES.items()
    ]
