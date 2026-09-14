import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "invoice_booking")
TOLERANCE_EUR = os.getenv("TOLERANCE_EUR", "0.02")

# Optional hosted open-weight LLM extraction (extraction/llm_extractor.py).
# Open-source alternative to a closed-source model (e.g. Claude): any
# OpenAI-compatible chat-completions endpoint serving an open-weight model
# (Together.ai/Groq/Fireworks running Llama, Qwen, DeepSeek, ...). Extraction
# falls back to the deterministic regex extractor whenever LLM_API_KEY is
# unset, so the system remains fully functional offline. Never hardcode the
# key here -- set it via environment variable / secrets manager.
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.together.xyz/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")
