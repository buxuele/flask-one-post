#!/usr/bin/env python3
"""
独立的 Twitter/X 发布工具
直接修改下面的 CONTENT 和 IMAGE_PATHS 变量即可
"""

import os
import requests
from pathlib import Path
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

# ============== 在这里修改发布内容 ==============
CONTENT = """读书不会用，或许是傻子。"""

IMAGE_PATHS = [
    # 图片路径，不需要图片就留空列表 []
    "g.jpg"
]
# ===============================================

def _load_env():
    """加载环境变量"""
    env_path = Path(__file__).resolve().parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    return {
        'api_key': os.getenv('X_API_KEY', '').strip(),
        'api_key_secret': os.getenv('X_API_KEY_SECRET', '').strip(),
        'access_token': os.getenv('X_ACCESS_TOKEN', '').strip(),
        'access_token_secret': os.getenv('X_ACCESS_TOKEN_SECRET', '').strip(),
        'callback_url': os.getenv('X_CALLBACK_URL', 'http://localhost:8080/callback').strip()
    }

def _upload_media(image_path, creds):
    """上传图片到 Twitter"""
    url = 'https://upload.twitter.com/1.1/media/upload.json'
    oauth = OAuth1(
        client_key=creds['api_key'],
        client_secret=creds['api_key_secret'],
        resource_owner_key=creds['access_token'],
        resource_owner_secret=creds['access_token_secret']
    )
    
    with open(image_path, 'rb') as f:
        files = {'media': f}
        response = requests.post(url, auth=oauth, files=files, timeout=60)
    
    if response.status_code >= 400:
        raise RuntimeError(f'媒体上传失败: {response.status_code} {response.text}')
    
    return response.json().get('media_id_string')

def _post_tweet(content, media_ids, creds):
    """发布推文"""
    from xdk import Client
    from xdk.oauth1_auth import OAuth1
    
    oauth1 = OAuth1(
        creds['api_key'],
        creds['api_key_secret'],
        creds['callback_url'],
        creds['access_token'],
        creds['access_token_secret']
    )
    client = Client(auth=oauth1)
    
    body = {'text': content}
    if media_ids:
        body['media'] = {'media_ids': media_ids}
    
    return client.posts.create(body=body)

def publish_to_twitter(content, image_paths=None):
    """发布内容到 Twitter/X"""
    print(f'准备发布到 Twitter/X...')
    print(f'内容: {content[:50]}{"..." if len(content) > 50 else ""}')
    
    creds = _load_env()
    missing = [k for k, v in creds.items() if not v and k != 'callback_url']
    if missing:
        raise ValueError(f'环境变量未配置: {", ".join(missing)}')
    
    media_ids = []
    if image_paths:
        print(f'上传 {len(image_paths)} 张图片...')
        for img_path in image_paths:
            if not os.path.exists(img_path):
                print(f'  跳过: 图片不存在 {img_path}')
                continue
            media_id = _upload_media(img_path, creds)
            media_ids.append(media_id)
            print(f'  上传成功: {os.path.basename(img_path)}')
    
    print('正在发布推文...')
    response = _post_tweet(content, media_ids, creds)
    print('发布成功！')
    
    return response

if __name__ == '__main__':
    if not CONTENT.strip():
        print('错误: CONTENT 不能为空')
        exit(1)
    
    try:
        response = publish_to_twitter(CONTENT, image_paths=IMAGE_PATHS)
        print(f'推文链接: https://x.com/i/web/status/{response.data.id}')
    except Exception as e:
        print(f'发布失败: {e}')
        exit(1)
