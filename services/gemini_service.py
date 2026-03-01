import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# =========================================================================
# 诊断说明：google-genai 官方 SDK 在当前 Pydantic 环境下存在响应解析阻塞问题。
# 为了确保您的应用能够即刻投入运行且性能优越，我们直接使用 Google API REST 接口。
# 支持您提供的全部模型：gemini-3-flash-preview, gemini-2.5-flash-lite, gemini-2.5-flash
# =========================================================================

# 严格遵循您提供的模型列表
MODELS = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash"
]

def _call_gemini_api(prompt, system_instruction=None):
    api_key = os.getenv('GEMINI_API_KEY', '')
    
    for model_name in MODELS:
        try:
            # 这里的 URL 需要包含模型名称和 API KEY
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ]
            }
            
            # 如果有系统指令，添加到请求中
            if system_instruction:
                payload["system_instruction"] = {
                    "parts": [{"text": system_instruction}]
                }

            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                # 按照 Google API 响应结构提取文本
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        return candidate["content"]["parts"][0]["text"]
            else:
                print(f"模型 {model_name} 返回错误: {response.status_code} - {response.text}")
                continue
                
        except Exception as e:
            print(f"模型 {model_name} 请求异常: {e}")
            continue
            
    return None

def suggest_hashtags(content):
    if not content.strip():
        return []

    system_instruction = "You are a social media expert. Suggest exactly 6 hashtags for the given content: 3 in English and 3 in Chinese. Prefer popular topics that are commonly recognized on platforms like X (Twitter) and Zhihu. Return only the hashtags as a comma-separated list without # symbols. Format: English1, English2, English3, 中文1, 中文2, 中文3"
    prompt = f"Content: {content}"
    
    response = _call_gemini_api(prompt, system_instruction)
    if response:
        # 处理可能包含的原始回复内容 (有时候会带引号或额外的文字)
        tags = [tag.strip().replace('#', '') for tag in response.split(',') if tag.strip()]
        # 进一步清理，防止 AI 返回包含 "Here are the hashtags:" 之类的废话
        clean_tags = []
        for tag in tags:
            # 只保留没有空格、不包含“建议”等字样的词
            if ' ' not in tag and len(tag) < 20:
                clean_tags.append(tag)
        return clean_tags[:6] if clean_tags else ['AI', 'Tech', 'Innovation', '人工智能', '科技', '创新']
    
    return ['AI', 'Tech', 'Innovation', '人工智能', '科技', '创新']

def add_tags_to_content(content):
    """添加tags到内容末尾，不改写原文"""
    if not content.strip():
        return content
    
    # 获取tags
    tags = suggest_hashtags(content)
    if not tags:
        return content
    
    # 格式化tags (3个英文 + 3个中文)
    en_tags = [f"#{tag}" for tag in tags[:3]]
    zh_tags = [f"#{tag}" for tag in tags[3:6]]
    
    # 将tags添加到内容末尾
    all_tags = en_tags + zh_tags
    tags_str = " ".join(all_tags)
    
    return f"{content}\n\n{tags_str}"
