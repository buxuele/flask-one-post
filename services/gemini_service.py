import os
from groq import Groq

client = Groq(
    api_key=os.getenv('GROQ_API_KEY', ''),
)

def suggest_hashtags(content):
    if not content.strip():
        return []

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a social media expert. Suggest exactly 6 hashtags for the given content: 3 in English and 3 in Chinese. Return only the hashtags as a comma-separated list without # symbols. Format: English1, English2, English3, 中文1, 中文2, 中文3"
                },
                {
                    "role": "user",
                    "content": f"Content: {content}"
                }
            ],
            model="openai/gpt-oss-120b",
        )

        response = chat_completion.choices[0].message.content
        tags = [tag.strip().replace('#', '') for tag in response.split(',') if tag.strip()]
        return tags[:6]
    except Exception as e:
        print(f"Groq Error: {e}")
        return ['AI', 'Tech', 'Innovation', '人工智能', '科技', '创新']

def refine_content(content):
    if not content.strip():
        return content
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional editor. Improve the clarity and emotional impact of social media posts while keeping them concise. Return only the improved text."
                },
                {
                    "role": "user",
                    "content": f"Improve this content: {content}"
                }
            ],
            model="openai/gpt-oss-120b",
        )
        
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq Error: {e}")
        return content
