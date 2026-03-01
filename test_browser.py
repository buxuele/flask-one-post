from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    page.goto('http://localhost:5000')
    page.wait_for_load_state('networkidle')
    
    page.screenshot(path='D:/2026/flask-one-post/test_screenshots/homepage.png', full_page=True)
    print("Screenshot saved: homepage.png")
    
    page.goto('http://localhost:5000/history')
    page.wait_for_load_state('networkidle')
    
    page.screenshot(path='D:/2026/flask-one-post/test_screenshots/history.png', full_page=True)
    print("Screenshot saved: history.png")
    
    time.sleep(2)
    browser.close()
