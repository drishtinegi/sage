import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
client = genai.Client(api_key=API_KEY)


def _config(json_mode: bool, temperature: float | None, model_env: str):
    kwargs = dict(
        response_mime_type="application/json" if json_mode else None,
        temperature=temperature,
    )
    budget = os.environ.get("LLM_THINKING_BUDGET", "").strip()
    if budget and model_env == "LLM_MODEL_CHEAP":
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=int(budget))
    return types.GenerateContentConfig(**kwargs)


def generate(
    prompt: str,
    model_env: str = "LLM_MODEL_STRONG",
    json_mode: bool = True,
    temperature: float | None = None,
) -> str:
    config = _config(json_mode, temperature, model_env)
    models = [os.environ[model_env]]
    fallback = os.environ.get("LLM_MODEL_FALLBACK")
    if fallback and fallback not in models:
        models.append(fallback)

    last_error = None
    for model in models:
        for attempt in range(4):
            try:
                resp = client.models.generate_content(model=model, contents=prompt, config=config)
                return resp.text
            except ServerError as e:
                last_error = e
                wait = 2 ** attempt * 2
                print(f"[{model}] {e.code} busy, retrying in {wait}s...")
                time.sleep(wait)
            except ClientError as e:
                last_error = e
                print(f"[{model}] {e.code} not usable ({str(e)[:100]}), trying next model...")
                break
    raise RuntimeError(f"all models unavailable: {last_error}")