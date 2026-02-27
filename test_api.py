import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY', ''))

# 测试用户提供的模型名称
model_name = "gemini-3-flash-preview"

try:
    print(f"Testing {model_name} with google-genai...")
    response = client.models.generate_content(
        model=model_name,
        contents="hi"
    )
    print("Success!")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
