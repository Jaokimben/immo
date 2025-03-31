import requests
from bs4 import BeautifulSoup
import logging
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import time
import random
import re
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///annonces.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database model
class Annonce(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200))
    prix = db.Column(db.String(50))
    surface = db.Column(db.String(50))
    localisation = db.Column(db.String(200))
    description = db.Column(db.Text)
    source = db.Column(db.String(100))
    url = db.Column(db.String(500))
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()

def configure_browser():
    """Configure headless Chrome for Railway with proper resource management"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(options=options)
    """Get a configured browser instance with resource cleanup"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(options=options)

def scrape_with_requests(url, headers=None, expected_format='html'):
    """Browser-agnostic scraping using requests"""
    try:
        # Determine content type based on expected format
        content_type = {
            'html': 'text/html',
            'json': 'application/json'
        }.get(expected_format, 'text/html')

        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': content_type,
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        final_headers = {**default_headers, **(headers or {})}
        
        response = requests.get(
            url,
            headers=final_headers,
            timeout=10
        )
        response.raise_for_status()

        # First try JSON parsing if expected
        if expected_format == 'json':
            try:
                # First attempt to parse as JSON regardless of content-type
                return response.json()
            except ValueError:
                # If JSON parsing fails, check if we got HTML instead
                if '<!doctype html' in response.text.lower():
                    logger.warning(f"Received HTML instead of JSON from {url}")
                    raise ValueError("Received HTML response when expecting JSON")
                else:
                    logger.error(f"Invalid JSON content from {url}")
                    raise

        # Then try HTML parsing
        try:
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Failed to parse HTML from {url}: {str(e)}")
            raise ValueError(f"Could not parse response as either JSON or HTML")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Scraping error for {url}: {str(e)}")
        raise

def get_paris_suggestions():
    """Get Paris suggestions from the website with Selenium fallback"""
    json_url = "https://api.seloger.com/suggestions/paris"
    result = None
    
    # Try API first with enhanced headers
    try:
        data = scrape_with_requests(
            json_url,
            headers={
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'fr-FR,fr;q=0.9',
                'Referer': 'https://www.seloger.com/'
            },
            expected_format='json'
        )
        if isinstance(data, dict) and data.get('suggestions'):
            return data['suggestions'][:10]
    except Exception as json_error:
        logger.warning(f"API request failed: {str(json_error)}")
    
    # Fallback to browser automation
    browser = None
    try:
        browser = configure_browser()
        browser.get("https://www.seloger.com/suggestions/paris")
        time.sleep(2 + random.uniform(0.5, 1.5))  # Randomized delay
        
        # Use multiple selector strategies
        selectors = [
            (By.CSS_SELECTOR, ".suggestions-list li"),
            (By.CSS_SELECTOR, "[data-testid='suggestion-item']"),
            (By.XPATH, "//ul/li/a")
        ]
        
        suggestions = []
        for selector in selectors:
            try:
                elements = browser.find_elements(*selector)
                if elements:
                    suggestions.extend([e.text.strip() for e in elements if e.text.strip()])
                    if suggestions:
                        break
            except NoSuchElementException:
                continue
        
        return list(set(suggestions))[:10]
        
    except Exception as e:
        logger.error(f"Browser fallback failed: {str(e)}")
        return []
    finally:
        if browser:
            browser.quit()
    try:
        response = requests.get(
            url,
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10
        )
        response.raise_for_status()
        
        # Check if response is HTML before parsing
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type and 'application/json' not in content_type:
            logger.warning(f"Unexpected content type: {content_type}")
            raise ValueError(f"Unsupported content type: {content_type}")
            
        soup = BeautifulSoup(response.content, 'html.parser')
        suggestions = []
        
        # Try multiple selector strategies
        selectors = [
            {'type': 'css', 'pattern': '.suggestions-list li'},
            {'type': 'css', 'pattern': '.autocomplete-items div'},
            {'type': 'css', 'pattern': '[class*="suggestion"]'},
            {'type': 'xpath', 'pattern': '//ul/li/a'},
        ]
        
        for selector in selectors:
            try:
                if selector['type'] == 'css':
                    items = soup.select(selector['pattern'])
                else:
                    items = soup.xpath(selector['pattern'])
                
                if items:
                    suggestions.extend(
                        item.get_text().strip()
                        for item in items
                        if item.get_text().strip()
                    )
                    if suggestions:
                        break
            except Exception:
                continue
                
        return list(set(suggestions))[:10]  # Dedupe and limit
        
    except Exception as html_error:
        logger.error(f"HTML scraping failed: {str(html_error)}")
        return []

def scrap_seloger():
    """Scrape SeLoger using requests"""
    logger.info("Starting SeLoger scraping")
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            url = f'https://www.seloger.com/achat/immobilier/{ville}/'
            logger.info(f"Scraping {ville} at {url}")
            
            try:
                soup = scrape_with_requests(url)
                # Add parsing logic here
                # Example: annonces = soup.find_all('div', class_='listing')
                
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                logger.error(f"Error scraping {ville}: {str(e)}")
                continue
                
        logger.info("Finished SeLoger scraping")
        
    except Exception as e:
        logger.error(f"SeLoger scraping failed: {str(e)}")
        raise

# Similar functions for other sites (PAP, LeBonCoin, etc.)
# Would follow same pattern as scrap_seloger()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recherche')
def recherche():
    # Search logic here
    return jsonify([])

@app.route('/suggestions')
def suggestions():
    query = request.args.get('q', '').lower()
    if query == 'paris':
        try:
            suggestions = get_paris_suggestions()
            return jsonify(suggestions)
        except Exception as e:
            logger.error(f"Error processing suggestions for Paris: {str(e)}")
            return jsonify([])
    return jsonify([])

# Railway requires this specific host binding
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)