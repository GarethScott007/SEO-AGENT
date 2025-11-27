# This is a module for crawl_site()—already integrated in main script.
# Expand as needed for deeper crawls.
from playwright.sync_api import sync_playwright
import requests

def find_404s(base_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url)
        links = page.query_selector_all('a')
        broken = []
        for link in links:
            href = link.get_attribute('href')
            if href and not href.startswith('#'):
                resp = requests.get(base_url + href, timeout=10)
                if resp.status_code == 404:
                    broken.append(href)
        browser.close()
    return broken
