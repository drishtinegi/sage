import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
resp = client.models.generate_content(
    model=os.environ["LLM_MODEL_CHEAP"],
    contents="Reply with the single word: ready",
)
print(resp.text)