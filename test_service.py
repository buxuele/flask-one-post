import os
import sys
from dotenv import load_dotenv

# 添加当前目录及 services 目录到 sys.path
sys.path.append(os.getcwd())

from services import gemini_service

load_dotenv()

content = "这是个测试内容，看看 AI 能否润色和建议话题。"

print("测试润色功能...")
refined = gemini_service.refine_content(content)
print(f"润色后: {refined}")

print("\n测试话题建议...")
tags = gemini_service.suggest_hashtags(content)
print(f"建议的话题: {tags}")
