import os
from google import genai

client = genai.Client(api_key="TEST_KEY")
print("Client created")
# Just listing models, wait, I did that and it crashed at Pydantic.
# Let's try to just check the version.
import pydantic
print(f"Pydantic version: {pydantic.__version__}")
