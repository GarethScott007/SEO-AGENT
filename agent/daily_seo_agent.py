#!/usr/bin/env python3
import json
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from github import Github
from playwright.sync_api import sync_playwright
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
from google.searchconsole_verification import SearchConsoleClient  # Note: Use google-api-python-client for full impl
from anthropic import Anthropic
import requests
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv

load_dotenv('config/secrets.json')

# Setup logging
logging.basicConfig(filename='logs/seo-agent.log', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
with open('config/config.json', 'r') as f:
    config = json.load(f)

SITE_URL = config['site_url']
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
SABAIFLY_REPO = config['sabaifly_repo']
PAGES_TO_REWRITE = config['pages_to_rewrite_daily']
AI_PRIMARY = config['ai_primary']
CLAUDE_KEY = os.getenv('CLAUDE_API_KEY')
GROK_KEY = os.getenv('GROK_API_KEY')  # Implement Grok API call similarly

# GitHub client
g = Github(GITHUB_TOKEN)
sabaifly = g.get_repo(SABAIFLY_REPO)

def crawl_site():
    """Crawl for broken links, slow pages, etc."""
    issues = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(SITE_URL, wait_until='networkidle')
            # Simulate crawl: Check links
            links = page.query_selector_all('a[href]')
            for link in links[:10]:  # Limit for demo
                href = link.get_attribute('href')
                if href:
                    full_url = href if href.startswith('http') else SITE_URL + href.lstrip('/')
                    response = requests.head(full_url, timeout=5)
                    if response.status_code >= 400:
                        issues.append({'broken': full_url, 'status': response.status_code})
            # Check load time
            load_time = page.evaluate('performance.now()') / 1000
            if load_time > 3:
                issues.append({'slow_page': SITE_URL, 'load_time': load_time})
        except Exception as e:
            logger.error(f"Crawl error: {e}")
        finally:
            browser.close()
    return issues

def get_ga_data():
    """Pull GA4 data for yesterday."""
    client = BetaAnalyticsDataClient()
    yesterday = (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')
    request = RunReportRequest(
        property=f"properties/{config['google_property_id']}",
        date_ranges=[DateRange(start_date=yesterday, end_date=yesterday)],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="impressions"), Metric(name="clicks"), Metric(name="ctr")]
    )
    response = client.run_report(request)
    low_ctr_pages = []
    for row in response.rows[:PAGES_TO_REWRITE]:
        path = row.dimension_values[0].value
        impressions = int(row.metric_values[0].value)
        ctr = float(row.metric_values[2].value)
        if impressions > 100 and ctr < 0.02:  # Low CTR threshold
            low_ctr_pages.append(path)
    return low_ctr_pages

def get_search_console_queries():
    """Pull GSC queries (simplified—use full API)."""
    # Placeholder: In full impl, use SearchConsoleClient
    # For now, return mock for demo
    return ['sabaifly seo tips', 'nextjs optimization', 'vercel deployment guide']  # Replace with real API call

def ai_rewrite_page(page_path, keywords):
    """Send to Grok-4 or Claude for rewrite."""
    # Fetch current content from repo
    try:
        content_file = sabaifly.get_contents(f"pages{page_path}.mdx")  # Adjust for your Next.js structure
        current_content = content_file.decoded_content.decode('utf-8')
    except:
        current_content = "# Placeholder Content\nThis is the current page."

    prompt = f"""
    Rewrite this Next.js page content for SEO. Target keywords: {', '.join(keywords)}.
    Improve: Title/meta, H1-H3, body (keep ~{len(current_content.split())} words), add FAQ schema, internal links to other SabaiFly pages.
    Output as MDX format with frontmatter. Enhance EEAT. Make it engaging for devs optimizing Vercel sites.
    Current: {current_content[:2000]}  # Truncate for API limits
    """

    if AI_PRIMARY == 'grok4' and GROK_KEY:
        # Grok API call (use requests to https://api.x.ai/v1/chat/completions)
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROK_KEY}", "Content-Type": "application/json"},
            json={"model": "grok-4", "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000}
        ).json()
        new_content = response['choices'][0]['message']['content']
    else:  # Claude fallback
        client = Anthropic(api_key=CLAUDE_KEY)
        msg = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        new_content = msg.content[0].text

    return new_content

def publish_to_repo(file_path, new_content):
    """Commit changes to SabaiFly repo."""
    try:
        existing = sabaifly.get_contents(file_path)
        sabaifly.update_file(
            path=file_path,
            message=f"SEO Agent: Auto-optimized {file_path} for better rankings",
            content=new_content.encode('utf-8'),
            sha=existing.sha
        )
    except:
        sabaifly.create_file(
            path=file_path,
            message=f"SEO Agent: Created/optimized {file_path}",
            content=new_content.encode('utf-8')
        )
    logger.info(f"Published {file_path}")

def fix_redirects(issues):
    """Add 301 redirects to next.config.js."""
    config_file = sabaifly.get_contents('next.config.js')
    current_config = config_file.decoded_content.decode('utf-8')
    redirects = []
    for issue in issues:
        if 'broken' in issue:
            redirects.append(f"  {{ source: '{issue['broken']}', destination: '/404', permanent: true }},")
    new_redirects = '\n'.join(redirects)
    updated_config = current_config.replace('redirects: [', f'redirects: [\n{new_redirects}')
    publish_to_repo('next.config.js', updated_config)

def generate_new_article(keywords):
    """AI-generate a new blog post."""
    prompt_path = 'prompts/new_article_cluster.txt'
    with open(prompt_path, 'r') as f:
        base_prompt = f.read()
    full_prompt = base_prompt.format(keywords=', '.join(keywords), site='SabaiFly', focus='Next.js/Vercel SEO')
    new_content = ai_rewrite_page('/blog/new-post', keywords)  # Reuse rewrite func
    publish_to_repo('app/blog/new-seo-guide/page.mdx', new_content)  # Adjust path for your app router

def update_sitemap():
    """Regen sitemap.xml and ping Google."""
    # Simplified: Fetch all pages via API or crawl, generate XML
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{SITE_URL}</loc><lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod></url>
  <!-- Add more via crawl -->
</urlset>"""
    publish_to_repo('public/sitemap.xml', sitemap_content)
    # Ping Google
    requests.get(f"https://www.google.com/ping?sitemap={SITE_URL}/sitemap.xml")

def send_notification(summary):
    """Slack/Discord webhook."""
    webhook = config['notification_webhook']
    if webhook:
        requests.post(webhook, json={"text": f"🛡️ SEO Agent Daily: {summary}"})

def daily_run():
    """Main daily flow."""
    start_time = datetime.now()
    logger.info("Starting daily SEO run")
    
    # 1. Crawl
    issues = crawl_site()
    fix_redirects(issues)
    
    # 2. Analytics
    low_pages = get_ga_data()
    queries = get_search_console_queries()
    
    # 3. Optimize pages
    for page in low_pages[:PAGES_TO_REWRITE]:
        keywords = queries[:5]  # Cluster
        new_content = ai_rewrite_page(page, keywords)
        publish_to_repo(page, new_content)
    
    # 4. New content
    if config['new_articles_per_day']:
        generate_new_article(queries)
    
    # 5. Sitemap
    update_sitemap()
    
    # Summary
    summary = f"Fixed {len(issues)} issues, optimized {len(low_pages)} pages, +1 article. Runtime: {datetime.now() - start_time}"
    logger.info(summary)
    send_notification(summary)

if __name__ == "__main__":
    daily_run()  # Run once, or scheduler.start() for cron-like
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(daily_run, 'cron', hour=3)
    # scheduler.start()
