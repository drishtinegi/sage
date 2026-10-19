import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
client = genai.Client(api_key=API_KEY)


def generate(prompt: str, model_env: str = "LLM_MODEL_STRONG", json_mode: bool = True) -> str:
    config = types.GenerateContentConfig(
        response_mime_type="application/json" if json_mode else None,
    )
    # try the requested model, then the fallback model if there is one
    models = [os.environ[model_env]]
    fallback = os.environ.get("LLM_MODEL_FALLBACK")
    if fallback and fallback not in models:
        models.append(fallback)

    last_error = None
    for model in models:
        for attempt in range(4):
            try:
                resp = client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                return resp.text
            except ServerError as e:
                last_error = e
                wait = 2 ** attempt * 2  # 2, 4, 8, 16 seconds
                print(f"[{model}] {e.code} busy, retrying in {wait}s...")
                time.sleep(wait)
            except ClientError as e:
                last_error = e
                print(f"[{model}] {e.code} not usable, trying next model...")
                break
    raise RuntimeError(f"all models unavailable: {last_error}")