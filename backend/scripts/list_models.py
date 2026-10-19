import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", encoding="utf-8-sig")

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
for m in client.models.list():
    if "generateContent" in (m.supported_actions or []):
        print(m.name)