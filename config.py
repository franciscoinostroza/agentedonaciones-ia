import os
import time
from openai import OpenAI

_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

IA_API_KEY = os.environ.get("IA_API_KEY", "")
IA_BASE_URL = os.environ.get("IA_BASE_URL", "https://opencode.ai/zen/v1")
IA_MODEL = os.environ.get("IA_MODEL", "deepseek-v4-flash-free")

_cliente = None


def get_cliente():
    global _cliente
    if _cliente is None and IA_API_KEY:
        _cliente = OpenAI(api_key=IA_API_KEY, base_url=IA_BASE_URL)
    return _cliente


def set_api_key(key, base_url=None, model=None):
    global _cliente
    os.environ["IA_API_KEY"] = key
    if base_url:
        os.environ["IA_BASE_URL"] = base_url
    if model:
        os.environ["IA_MODEL"] = model
    _cliente = OpenAI(api_key=key, base_url=base_url or IA_BASE_URL)


_CHAT_MAX_RETRIES = 2
_CHAT_TIMEOUT = 30


def chat(messages, model=None, temperature=0.3, max_tokens=8000):
    cliente = get_cliente()
    if not cliente:
        return None
    last_error = None
    for intento in range(_CHAT_MAX_RETRIES):
        try:
            resp = cliente.chat.completions.create(
                model=model or IA_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=_CHAT_TIMEOUT,
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_error = e
            if intento < _CHAT_MAX_RETRIES - 1:
                time.sleep(1.5 ** intento)
    return f"[Error IA: {last_error}]"
