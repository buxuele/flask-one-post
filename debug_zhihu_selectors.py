import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

COOKIES_FILE = Path('cookies.json')
ZHIHU_URL = 'https://www.zhihu.com/'

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport=None)
        
        if COOKIES_FILE.exists():
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
            print("Cookies loaded.")
        
        page = context.new_page()
        page.goto(ZHIHU_URL)
        page.wait_for_timeout(3000)
        
        print("Searching for '分享此刻的想法'...")
        # Get all elements containing the text
        elements = page.locator("div:has-text('分享此刻的想法')")
        count = elements.count()
        print(f"Found {count} elements with 'div:has-text('分享此刻的想法')'")
        
        for i in range(count):
            el = elements.nth(i)
            # Find the smallest element (deepest) that has the text
            # Usually the one we want to click is a div or span
            tag = el.evaluate("node => node.tagName")
            text = el.inner_text()
            print(f"Element {i}: Tag={tag}, Text='{text[:30]}...'")
            if "分享此刻的想法" in text:
                 # Check if it's visible and clickable
                 is_visible = el.is_visible()
                 print(f"  Visible: {is_visible}")

        # Check for placeholder
        placeholders = page.locator("[placeholder]")
        p_count = placeholders.count()
        for i in range(p_count):
            p = placeholders.nth(i).get_attribute("placeholder")
            if p:
                print(f"Placeholder found: '{p}'")

        browser.close()

if __name__ == "__main__":
    debug()
