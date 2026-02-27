import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY', '')
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    print("Calling API...")
    r = requests.get(url)
    print(f"Status: {r.status_code}")
    models = r.json()
    if "models" in models:
        for m in models["models"]:
            print(m["name"])
    else:
        print(models)
except Exception as e:
    print(f"Error: {e}")
