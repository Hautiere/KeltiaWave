import os
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/transcription/models",
    tags=["transcription-models"]
)

# -------------------------------------------------------------------
# Source de vérité : modèles de transcription (ASR)
# -------------------------------------------------------------------

MODELS_ROOT = Path(os.getenv("MODELS_ROOT", str(Path(__file__).resolve().parents[2] / "models")))
WHISPER_BR_DIR = Path(os.getenv("WHISPER_BR_MODEL_PATH", str(MODELS_ROOT / "whisper-breton-ct2")))
WHISPER_CY_DIR = Path(os.getenv("WHISPER_CY_MODEL_PATH", str(MODELS_ROOT / "whisper-welsh-ct2")))
VOSK_BR_DIR = Path(os.getenv("VOSK_MODEL_PATH", str(MODELS_ROOT / "vosk-model-br-25.02")))


TRANSCRIPTION_MODELS_STATUS = {
    "default_engine": "whisper",   # ✅ AJOUT

    "engines": {
        "whisper": {
            "languages": {
                "br": {
                    "available": WHISPER_BR_DIR.exists(),
                    "default_model_id": "whisper_ct2_large_int8_v2024_10"
                },
                "cy": {
                    "available": WHISPER_CY_DIR.exists(),
                    "default_model_id": "whisper_ct2_large_int8_v2024_10"
                },
                "kw": {
                    "available": False,
                    "reason": "no reliable ASR model available"
                }
            }
        },
        "vosk": {
            "languages": {
                "br": {
                    "available": VOSK_BR_DIR.exists(),
                    "default_model_id": "vosk_br_v1"
                },
                "cy": {
                    "available": False,
                    "reason": "welsh Vosk model not installed and runtime is still Breton-only"
                },
                "kw": {
                    "available": False
                }
            }
        }
    },
    "models": {
        "whisper_ct2_large_int8_v2024_10": {
            "engine": "whisper",
            "provider": "ctranslate2",
            "name": "whisper-large",
            "variant": "int8",
            "version": "2024-10-01"
        },
        "vosk_br_v1": {
            "engine": "vosk",
            "provider": "vosk",
            "name": "vosk-model-br",
            "variant": "small",
            "version": "0.3"
        },
        "vosk_cy_v1": {
            "engine": "vosk",
            "provider": "vosk",
            "name": "vosk-model-cy",
            "variant": "small",
            "version": "0.3"
        }
    }
}

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@router.get("/status")
def transcription_models_status():
    """
    List available transcription engines and models.
    Declarative endpoint (no runtime logic).
    """
    return TRANSCRIPTION_MODELS_STATUS
