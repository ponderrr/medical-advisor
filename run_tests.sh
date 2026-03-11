#!/bin/bash
source /home/frosty/medical-advisor/venv/bin/activate
cd /home/frosty/medical-advisor
python -m pytest tests/test_reddit_scraper.py -v 2>&1
