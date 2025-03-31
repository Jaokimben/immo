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
from sqlalchemy import or_

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
        # Ajout de plusieurs villes principales pour avoir plus de données
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            url = f'https://www.seloger.com/recherche/achat/{ville}/'
            driver.get(url)
            driver.implicitly_wait(10)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            annonces = soup.find_all('div', class_='c-pa-list')
            
            for annonce in annonces:
                titre = annonce.find('div', class_='c-pa-title').text.strip()
                prix = annonce.find('div', class_='c-pa-price').text.strip()
                surface = annonce.find('div', class_='c-pa-criterion').text.strip()
                
                # Amélioration de l'extraction de la localisation
                localisation_div = annonce.find('div', class_='c-pa-city')
                if localisation_div:
                    localisation = localisation_div.text.strip()
                    # Nettoyage de la localisation
                    localisation = localisation.replace('\n', ' ').replace('  ', ' ').strip()
                else:
                    localisation = ville
                
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
            
            # Petit délai entre chaque ville pour éviter d'être bloqué
            time.sleep(2)
        
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
        .filter(
            db.or_(
                Annonce.localisation.ilike(f"%{query}%"),
                Annonce.localisation.ilike(f"%{query.capitalize()}%"),
                Annonce.localisation.ilike(f"%{query.upper()}%")
            )
        )\
        .distinct()\
        .order_by(Annonce.localisation)\
        .limit(5)\
        .all()
    
    # Si aucune suggestion n'est trouvée, on essaie avec une recherche plus large
    if not suggestions:
        suggestions = db.session.query(Annonce.localisation)\
            .filter(
                db.or_(
                    Annonce.localisation.ilike(f"%{query[:2]}%"),
                    Annonce.localisation.ilike(f"%{query[:2].capitalize()}%")
                )
            )\
            .distinct()\
            .order_by(Annonce.localisation)\
            .limit(5)\
            .all()
    
    return jsonify([s[0] for s in suggestions])

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 