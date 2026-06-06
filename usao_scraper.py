pip install -r requirements_scraper.txt

# Test on 2 districts, 2 pages each first
python usao_scraper.py --districts usao-sc usao-sdny --limit 2 --verbose

# Full run — all 94 districts
python usao_scraper.py --output cases.json
