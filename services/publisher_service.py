import io
import json
import os
import traceback
from pathlib import Path

import requests
from requests_oauthlib import OAuth1 as RequestsOAuth1
from xdk import Client
from xdk.oauth1_auth import OAuth1
from playwright.sync_api import sync_playwright
from PIL import Image
from dotenv import dotenv_values

COOKIES_FILE = os.getenv('ZHIHU_COOKIES_FILE', 'cookies.json')
ZHIHU_URL = 'https://www.zhihu.com/'
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'
_ENV_CACHE = None

def _emit(progress, message):
    if progress:
        progress(message)

def _load_env_file():
    global _ENV_CACHE
    if _ENV_CACHE is not None:
        return _ENV_CACHE
    if not ENV_PATH.exists():
        raise FileNotFoundError(f'未找到 .env: {ENV_PATH}')
    raw = dotenv_values(str(ENV_PATH))
    _ENV_CACHE = {k: v for k, v in raw.items() if v is not None}
    return _ENV_CACHE

def _get_x_env():
    env = _load_env_file()
    api_key = (env.get('X_API_KEY') or '').strip()
    api_key_secret = (env.get('X_API_KEY_SECRET') or '').strip()
    access_token = (env.get('X_ACCESS_TOKEN') or '').strip()
    access_token_secret = (env.get('X_ACCESS_TOKEN_SECRET') or '').strip()
    callback_url = (env.get('X_CALLBACK_URL') or 'http://localhost:8080/callback').strip()

    missing = []
    if not api_key:
        missing.append('X_API_KEY')
    if not api_key_secret:
        missing.append('X_API_KEY_SECRET')
    if not access_token:
        missing.append('X_ACCESS_TOKEN')
    if not access_token_secret:
        missing.append('X_ACCESS_TOKEN_SECRET')

    if missing:
        raise ValueError('X 环境变量未配置: ' + ', '.join(missing))

    return {
        'api_key': api_key,
        'api_key_secret': api_key_secret,
        'access_token': access_token,
        'access_token_secret': access_token_secret,
        'callback_url': callback_url
    }

def _upload_media_v1(image_path, creds):
    url = 'https://upload.twitter.com/1.1/media/upload.json'
    oauth = RequestsOAuth1(
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

    data = response.json()
    media_id = data.get('media_id_string')
    if not media_id:
        raise RuntimeError(f'未获取到 media_id: {data}')

    return media_id

def _get_xdk_client(creds):
    oauth1 = OAuth1(
        creds['api_key'],
        creds['api_key_secret'],
        creds['callback_url'],
        creds['access_token'],
        creds['access_token_secret']
    )
    return Client(auth=oauth1)

def publish_to_twitter(content, image_paths=None, progress=None):
    creds = _get_x_env()
    _emit(progress, 'X: 初始化客户端')
    client = _get_xdk_client(creds)

    media_ids = []
    for image_path in image_paths or []:
        if not image_path:
            continue
        if not os.path.exists(image_path):
            _emit(progress, f'X: 未找到图片 {image_path}')
            continue
        _emit(progress, f'X: 上传图片 {os.path.basename(image_path)}')
        media_ids.append(_upload_media_v1(image_path, creds))

    body = {'text': content}
    if media_ids:
        body['media'] = {'media_ids': media_ids}

    _emit(progress, 'X: 发送内容')
    response = client.posts.create(body=body)
    _emit(progress, 'X: 发布完成')
    return response

def _load_cookies(context, progress=None):
    if not os.path.exists(COOKIES_FILE):
        raise FileNotFoundError(f'未找到 {COOKIES_FILE}')

    with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
        raw_cookies = json.load(f)

    cookies = [{
        'name': c['name'],
        'value': c['value'],
        'domain': c['domain'],
        'path': c['path'],
        'expires': c.get('expirationDate', -1),
        'httpOnly': c.get('httpOnly', False),
        'secure': c.get('secure', False)
    } for c in raw_cookies]

    context.add_cookies(cookies)
    _emit(progress, '知乎: Cookies 已加载')

def _save_cookies(context, progress=None):
    cookies = context.cookies()
    with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)
    _emit(progress, '知乎: Cookies 已保存')

def _copy_image_to_clipboard(image_path, progress=None):
    absolute_path = Path(image_path).resolve()
    img = Image.open(absolute_path)
    output = io.BytesIO()
    img.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]
    output.close()

    import win32clipboard
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()
    _emit(progress, '知乎: 图片已复制到剪贴板')

def _post_idea(page, content, image_paths, progress=None):
    _emit(progress, '知乎: 打开想法输入框')
    page.get_by_text('分享此刻的想法').click()
    page.wait_for_timeout(1500)

    _emit(progress, '知乎: 填写内容')
    editor = page.get_by_role('textbox').nth(1)
    editor.fill(content)
    page.wait_for_timeout(800)

    if image_paths:
        for img_path in image_paths:
            if img_path and os.path.exists(img_path):
                _emit(progress, f'知乎: 处理图片 {os.path.basename(img_path)}')
                _copy_image_to_clipboard(img_path, progress)
                editor.focus()
                page.wait_for_timeout(300)
                page.keyboard.press('Control+V')
                page.wait_for_timeout(8000)

    _emit(progress, '知乎: 点击发布')
    page.get_by_role('button', name='发布').click()
    page.wait_for_timeout(2000)
    
    _emit(progress, '知乎: 发布完成')

def publish_to_zhihu(content, image_paths=None, progress=None):
    # 收集多个图片路径
    valid_image_paths = [p for p in (image_paths or []) if p and os.path.exists(p)]

    _emit(progress, '知乎: 启动浏览器')
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport=None)
            
            if os.path.exists(COOKIES_FILE):
                _load_cookies(context, progress)
            
            page = context.new_page()

            # 参考 zhihu_post.py 的流程：先打开首页 -> 加载 cookies -> 刷新 -> 发布
            _emit(progress, '知乎: 打开首页')
            page.goto(ZHIHU_URL)
            page.wait_for_timeout(1500)

            _load_cookies(context, progress)
            _emit(progress, '知乎: 刷新页面以应用 Cookies')
            page.reload()
            page.wait_for_timeout(2000)

            _post_idea(page, content, valid_image_paths, progress)
            _save_cookies(context, progress)
            
        return True
    except Exception as e:
        _emit(progress, f'知乎: 发布出错 - {str(e)}')
        raise
    finally:
        if browser:
            try:
                browser.close()
            except:
                pass

def publish_to_both(content, platforms, image_paths=None, progress=None):
    results = {'twitter': False, 'zhihu': False, 'messages': []}
    platforms_set = set(platforms or [])

    if 'twitter' in platforms_set:
        _emit(progress, '准备发布到 X，因为已选择 X 平台')
        try:
            publish_to_twitter(content, image_paths=image_paths, progress=progress)
            results['twitter'] = True
            results['messages'].append('X 发布成功')
        except Exception as e:
            traceback.print_exc()
            results['messages'].append(f'X 发布失败: {e}')

    if 'zhihu' in platforms_set:
        _emit(progress, '准备发布到知乎，因为已选择知乎平台')
        try:
            publish_to_zhihu(content, image_paths=image_paths, progress=progress)
            results['zhihu'] = True
            results['messages'].append('知乎 发布成功')
        except Exception as e:
            traceback.print_exc()
            results['messages'].append(f'知乎 发布失败: {e}')

    if not results['messages']:
        results['messages'].append('未选择发布平台')

    return results
