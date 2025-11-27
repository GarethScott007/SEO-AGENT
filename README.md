# SEO-AGENT for SabaiFly

Autonomous daily SEO optimizer for Next.js 16 + Vercel sites.

## Quick Start
1. Add secrets to GitHub repo settings (see config/secrets.example.json).
2. On VPS: `git clone https://github.com/GarethScott007/SEO-AGENT.git && cd SEO-AGENT && docker compose up -d`
3. First run: `docker exec seo-agent python agent/daily_seo_agent.py`

## What It Does Daily
- Crawls site for issues (404s, slow pages).
- Pulls GA4/Search Console data.
- AI-rewrites 3 underperforming pages via Grok-4/Claude.
- Generates 1 new article.
- Pushes to your SabaiFly repo → auto-deploys on Vercel.
- Fixes redirects in next.config.js.
- Pings Google with updated sitemap.

## Prompts Folder
Battle-tested for 40%+ CTR lifts.

For support: Reply to Grok convo.
