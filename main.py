import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

load_dotenv(Path(__file__).with_name(".env"))

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY is missing. Add it to the .env file next to main.py.")

client = genai.Client(api_key=api_key)

models = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.6-flash",
]

last_error = None
for model in models:
    try:
        response = client.models.generate_content(
            model=model,
            contents="Explain React Native in simple words.",
        )
        print(response.text)
        break
    except APIError as exc:
        last_error = exc
else:
    raise SystemExit(f"Gemini API error: {last_error}")
