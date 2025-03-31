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
                return response.json()
            except ValueError:
                logger.warning(f"Failed to parse JSON from {url}, trying HTML")

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
    """Get Paris suggestions from the website"""
    try:
        url = "https://www.seloger.com/suggestions/paris"
        
        # First attempt - try direct JSON API
        try:
            response = requests.get(
                url,
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0'
                },
                timeout=10
            )
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'suggestions' in data:
                        return data['suggestions']
                except ValueError:
                    pass  # Fall through to HTML parsing
        except requests.RequestException:
            pass  # Fall through to HTML parsing

        # Second attempt - HTML parsing fallback
        soup = scrape_with_requests(url)
        suggestions = []
        
        # Try multiple selector patterns
        selectors = [
            '.suggestion-item',
            '.autocomplete-item',
            '[class*="suggestion"]',
            '[class*="auto-complete"]',
            '[class*="predictive"]',
            'li > a',  # Common pattern for suggestion lists
            'div > a'   # Another common pattern
        ]
        
        for selector in selectors:
            items = soup.select(selector)
            if items:
                suggestions.extend(item.get_text(strip=True) for item in items if item.get_text(strip=True))
                if suggestions:  # Stop at first successful selector
                    break
                    
        return suggestions[:10]  # Return max 10 suggestions
        
    except Exception as e:
        logger.error(f"Error getting Paris suggestions: {str(e)}")
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

if __name__ == '__main__':
    app.run()