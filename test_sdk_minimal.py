import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY', ''))
model_name = "gemini-3-flash-preview"

try:
    print(f"Minimal test with {model_name}...")
    # 极简模式：不显式使用 sys_instruction
    response = client.models.generate_content(
        model=model_name,
        contents="hi"
    )
    print("Success!")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")




