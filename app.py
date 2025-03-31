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

def scrape_with_requests(url, headers=None, parse_json=False):
    """Browser-agnostic scraping using requests"""
    try:
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'application/json' if parse_json else 'text/html',
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

        if parse_json:
            return response.json()
        return BeautifulSoup(response.content, 'html.parser')
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {str(e)}")
        raise
    except ValueError as e:
        logger.error(f"Failed to parse response from {url}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Scraping error for {url}: {str(e)}")
        raise

def get_paris_suggestions():
    """Get Paris suggestions from the website"""
    try:
        url = "https://www.seloger.com/suggestions/paris"
        soup = scrape_with_requests(url)
        
        suggestions = []
        suggestion_items = soup.select('.suggestion-item')  # Update selector based on actual HTML
        
        for item in suggestion_items:
            suggestions.append(item.get_text(strip=True))
            
        return suggestions
        
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