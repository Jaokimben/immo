from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
import os
import time

load_dotenv()

app = Flask(__name__)

# Configuration de la base de données pour Railway
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///annonces.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

with app.app_context():
    db.create_all()

def scrap_seloger():
    # Configuration de Selenium pour Railway
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get('https://www.seloger.com/recherche/achat/')
        driver.implicitly_wait(10)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        annonces = soup.find_all('div', class_='c-pa-list')
        
        for annonce in annonces:
            titre = annonce.find('div', class_='c-pa-title').text.strip()
            prix = annonce.find('div', class_='c-pa-price').text.strip()
            surface = annonce.find('div', class_='c-pa-criterion').text.strip()
            localisation = annonce.find('div', class_='c-pa-city').text.strip()
            
            if not Annonce.query.filter_by(titre=titre).first():
                nouvelle_annonce = Annonce(
                    titre=titre,
                    prix=prix,
                    surface=surface,
                    localisation=localisation,
                    source='SeLoger',
                    url=annonce.find('a')['href']
                )
                db.session.add(nouvelle_annonce)
        
        db.session.commit()
    
    finally:
        driver.quit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recherche')
def recherche():
    criteres = {
        'prix_min': request.args.get('prix_min'),
        'prix_max': request.args.get('prix_max'),
        'surface_min': request.args.get('surface_min'),
        'surface_max': request.args.get('surface_max'),
        'localisation': request.args.get('localisation')
    }
    
    query = Annonce.query
    
    if criteres['prix_min']:
        query = query.filter(Annonce.prix >= criteres['prix_min'])
    if criteres['prix_max']:
        query = query.filter(Annonce.prix <= criteres['prix_max'])
    if criteres['surface_min']:
        query = query.filter(Annonce.surface >= criteres['surface_min'])
    if criteres['surface_max']:
        query = query.filter(Annonce.surface <= criteres['surface_max'])
    if criteres['localisation']:
        query = query.filter(
            Annonce.localisation.ilike(f"%{criteres['localisation']}%")
        )
    
    annonces = query.order_by(Annonce.date_ajout.desc()).all()
    
    # Ajout d'un délai artificiel de 1 seconde
    time.sleep(1)
    
    return jsonify([{
        'titre': a.titre,
        'prix': a.prix,
        'surface': a.surface,
        'localisation': a.localisation,
        'source': a.source,
        'url': a.url
    } for a in annonces])

@app.route('/actualiser')
def actualiser():
    scrap_seloger()
    return jsonify({'status': 'success'})

@app.route('/suggestions')
def suggestions():
    query = request.args.get('q', '').lower()
    if len(query) < 2:
        return jsonify([])
    
    # Ajout d'un délai artificiel de 0.5 seconde
    time.sleep(0.5)
    
    # Amélioration de la recherche des suggestions
    suggestions = db.session.query(Annonce.localisation)\
        .filter(Annonce.localisation.ilike(f"%{query}%"))\
        .distinct()\
        .order_by(Annonce.localisation)\
        .limit(5)\
        .all()
    
    return jsonify([s[0] for s in suggestions])

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 