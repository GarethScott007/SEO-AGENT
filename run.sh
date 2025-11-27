#!/bin/bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install
python agent/daily_seo_agent.py
