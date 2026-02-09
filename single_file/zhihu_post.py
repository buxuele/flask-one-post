#!/usr/bin/env python3
"""
独立的知乎发布工具
直接修改下面的 CONTENT 和 IMAGE_PATHS 变量即可
注意: 需要预先在浏览器中登录知乎并导出 cookies 到 cookies.json
"""

import os
import json
import io
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

# ============== 在这里修改发布内容 ==============
CONTENT = """读书不会用，或许是傻子。"""

IMAGE_PATHS = [
    # 图片路径，不需要图片就留空列表 []
    "g.jpg"
]
# ===============================================

COOKIES_FILE = Path(__file__).resolve().parent / 'cookies.json'
ZHIHU_URL = 'https://www.zhihu.com/'

def _load_cookies(context):
    """加载 cookies"""
    if not COOKIES_FILE.exists():
        raise FileNotFoundError(f'未找到 cookies 文件: {COOKIES_FILE}')
    
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

def _save_cookies(context):
    """保存 cookies"""
    cookies = context.cookies()
    with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)

def _copy_image_to_clipboard(image_path):
    """将图片复制到剪贴板（Windows 专用）"""
    import win32clipboard
    
    img = Image.open(image_path)
    output = io.BytesIO()
    img.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]
    output.close()
    
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()

def _post_idea(page, content, image_path=None):
    """发布想法"""
    page.get_by_text('分享此刻的想法').click()
    page.wait_for_timeout(1500)
    
    editor = page.get_by_role('textbox').nth(1)
    editor.fill(content)
    page.wait_for_timeout(800)
    
    if image_path and os.path.exists(image_path):
        _copy_image_to_clipboard(image_path)
        editor.focus()
        page.wait_for_timeout(300)
        page.keyboard.press('Control+V')
        page.wait_for_timeout(8000)
    
    page.get_by_role('button', name='发布').click()
    page.wait_for_timeout(2000)

def publish_to_zhihu(content, image_paths=None):
    """发布内容到知乎想法"""
    print(f'准备发布到知乎...')
    print(f'内容: {content[:50]}{"..." if len(content) > 50 else ""}')
    
    image_path = None
    for p in (image_paths or []):
        if p and os.path.exists(p):
            image_path = p
            break
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport=None)
        page = context.new_page()
        
        page.goto(ZHIHU_URL)
        page.wait_for_timeout(1500)
        
        _load_cookies(context)
        page.reload()
        page.wait_for_timeout(2000)
        
        _post_idea(page, content, image_path)
        _save_cookies(context)
        
        browser.close()
    
    print('知乎发布成功！')
    return True

if __name__ == '__main__':
    if not CONTENT.strip():
        print('错误: CONTENT 不能为空')
        exit(1)
    
    try:
        publish_to_zhihu(CONTENT, image_paths=IMAGE_PATHS)
    except Exception as e:
        print(f'发布失败: {e}')
        exit(1)
