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


def _config(json_mode, temperature, model_env, use_thinking):
    kwargs = dict(
        response_mime_type="application/json" if json_mode else None,
        temperature=temperature,
    )
    budget = os.environ.get("LLM_THINKING_BUDGET", "").strip()
    if use_thinking and budget and model_env == "LLM_MODEL_CHEAP":
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=int(budget))
    return types.GenerateContentConfig(**kwargs)


def generate(prompt, model_env="LLM_MODEL_STRONG", json_mode=True, temperature=None):
    models = [os.environ[model_env]]
    fallback = os.environ.get("LLM_MODEL_FALLBACK")
    if fallback and fallback not in models:
        models.append(fallback)

    last_error = None
    for model in models:
        use_thinking = True
        for attempt in range(4):
            config = _config(json_mode, temperature, model_env, use_thinking)
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
                if e.code == 400 and use_thinking and os.environ.get("LLM_THINKING_BUDGET", "").strip():
                    print(f"[{model}] 400 with thinking setting, retrying without it")
                    use_thinking = False
                    continue
                print(f"[{model}] {e.code} not usable: {str(e)[:300]}")
                break
    raise RuntimeError(f"all models unavailable: {last_error}")