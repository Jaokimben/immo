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
    print("Début du scraping SeLoger")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"Scraping de {ville} sur SeLoger")
            url = f'https://www.seloger.com/achat/immobilier/{ville}/'
            driver.get(url)
            driver.implicitly_wait(10)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            # Mise à jour des sélecteurs CSS
            annonces = soup.find_all('div', {'data-test': 'sl.card-container'})
            
            for annonce in annonces:
                try:
                    titre = annonce.find('div', {'data-test': 'sl.card-title'}).text.strip()
                    prix = annonce.find('div', {'data-test': 'sl.card-price'}).text.strip()
                    surface = annonce.find('div', {'data-test': 'sl.card-surface'}).text.strip()
                    localisation = annonce.find('div', {'data-test': 'sl.card-location'}).text.strip()
                    
                    if not Annonce.query.filter_by(titre=titre, source='SeLoger').first():
                        nouvelle_annonce = Annonce(
                            titre=titre,
                            prix=prix,
                            surface=surface,
                            localisation=localisation,
                            source='SeLoger',
                            url=annonce.find('a')['href']
                        )
                        db.session.add(nouvelle_annonce)
                        print(f"Nouvelle annonce ajoutée : {titre}")
                except Exception as e:
                    print(f"Erreur lors du traitement d'une annonce SeLoger : {str(e)}")
                    continue
            
            time.sleep(2)
        
        db.session.commit()
        print("Fin du scraping SeLoger")
    
    except Exception as e:
        print(f"Erreur lors du scraping SeLoger : {str(e)}")
    finally:
        driver.quit()

def scrap_pap():
    print("Début du scraping PAP")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"Scraping de {ville} sur PAP")
            url = f'https://www.pap.fr/annonce/achat-immobilier-{ville.lower()}'
            driver.get(url)
            driver.implicitly_wait(10)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            # Mise à jour des sélecteurs CSS
            annonces = soup.find_all('div', class_='announcement-item')
            
            for annonce in annonces:
                try:
                    titre = annonce.find('h2', class_='announcement-title').text.strip()
                    prix = annonce.find('div', class_='announcement-price').text.strip()
                    surface = annonce.find('div', class_='announcement-surface').text.strip()
                    localisation = annonce.find('div', class_='announcement-location').text.strip()
                    
                    if not Annonce.query.filter_by(titre=titre, source='PAP').first():
                        nouvelle_annonce = Annonce(
                            titre=titre,
                            prix=prix,
                            surface=surface,
                            localisation=localisation,
                            source='PAP',
                            url=annonce.find('a')['href']
                        )
                        db.session.add(nouvelle_annonce)
                        print(f"Nouvelle annonce ajoutée : {titre}")
                except Exception as e:
                    print(f"Erreur lors du traitement d'une annonce PAP : {str(e)}")
                    continue
            
            time.sleep(2)
        
        db.session.commit()
        print("Fin du scraping PAP")
    
    except Exception as e:
        print(f"Erreur lors du scraping PAP : {str(e)}")
    finally:
        driver.quit()

def scrap_leboncoin():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            url = f'https://www.leboncoin.fr/recherche?category=9&locations={ville}'
            driver.get(url)
            driver.implicitly_wait(10)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            annonces = soup.find_all('div', class_='styles_adCard')
            
            for annonce in annonces:
                titre = annonce.find('h3', class_='styles_title').text.strip()
                prix = annonce.find('span', class_='styles_price').text.strip()
                surface = annonce.find('span', class_='styles_surface').text.strip()
                localisation = annonce.find('span', class_='styles_location').text.strip()
                
                if not Annonce.query.filter_by(titre=titre, source='LeBonCoin').first():
                    nouvelle_annonce = Annonce(
                        titre=titre,
                        prix=prix,
                        surface=surface,
                        localisation=localisation,
                        source='LeBonCoin',
                        url=annonce.find('a')['href']
                    )
                    db.session.add(nouvelle_annonce)
            
            time.sleep(2)
        
        db.session.commit()
    
    finally:
        driver.quit()

def scrap_orpi():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            url = f'https://www.orpi.com/recherche/achat-immobilier-{ville.lower()}'
            driver.get(url)
            driver.implicitly_wait(10)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            annonces = soup.find_all('div', class_='property-card')
            
            for annonce in annonces:
                titre = annonce.find('h2', class_='property-title').text.strip()
                prix = annonce.find('div', class_='property-price').text.strip()
                surface = annonce.find('div', class_='property-surface').text.strip()
                localisation = annonce.find('div', class_='property-location').text.strip()
                
                if not Annonce.query.filter_by(titre=titre, source='Orpi').first():
                    nouvelle_annonce = Annonce(
                        titre=titre,
                        prix=prix,
                        surface=surface,
                        localisation=localisation,
                        source='Orpi',
                        url=annonce.find('a')['href']
                    )
                    db.session.add(nouvelle_annonce)
            
            time.sleep(2)
        
        db.session.commit()
    
    finally:
        driver.quit()

def scrap_logicimmo():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            url = f'https://www.logic-immo.com/achat-immobilier-{ville.lower()}'
            driver.get(url)
            driver.implicitly_wait(10)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            annonces = soup.find_all('div', class_='announcement-card')
            
            for annonce in annonces:
                titre = annonce.find('h3', class_='announcement-title').text.strip()
                prix = annonce.find('div', class_='announcement-price').text.strip()
                surface = annonce.find('div', class_='announcement-surface').text.strip()
                localisation = annonce.find('div', class_='announcement-location').text.strip()
                
                if not Annonce.query.filter_by(titre=titre, source='LogicImmo').first():
                    nouvelle_annonce = Annonce(
                        titre=titre,
                        prix=prix,
                        surface=surface,
                        localisation=localisation,
                        source='LogicImmo',
                        url=annonce.find('a')['href']
                    )
                    db.session.add(nouvelle_annonce)
            
            time.sleep(2)
        
        db.session.commit()
    
    finally:
        driver.quit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recherche')
def recherche():
    print("Début de la recherche")
    criteres = {
        'prix_min': request.args.get('prix_min'),
        'prix_max': request.args.get('prix_max'),
        'surface_min': request.args.get('surface_min'),
        'surface_max': request.args.get('surface_max'),
        'localisation': request.args.get('localisation')
    }
    
    print(f"Critères de recherche : {criteres}")
    
    query = Annonce.query
    
    if criteres['localisation']:
        query = query.filter(
            db.or_(
                Annonce.localisation.ilike(f"%{criteres['localisation']}%"),
                Annonce.localisation.ilike(f"%{criteres['localisation'].capitalize()}%"),
                Annonce.localisation.ilike(f"%{criteres['localisation'].upper()}%")
            )
        )
    
    annonces = query.order_by(Annonce.date_ajout.desc()).all()
    print(f"Nombre d'annonces trouvées : {len(annonces)}")
    
    # Filtrage des annonces en fonction des critères numériques
    annonces_filtrees = []
    for annonce in annonces:
        try:
            # Extraction du prix numérique
            prix_str = ''.join(filter(str.isdigit, annonce.prix))
            prix = int(prix_str) if prix_str else 0
            
            # Extraction de la surface numérique
            surface_str = ''.join(filter(str.isdigit, annonce.surface))
            surface = int(surface_str) if surface_str else 0
            
            # Application des filtres
            if criteres['prix_min'] and prix < int(criteres['prix_min']):
                continue
            if criteres['prix_max'] and prix > int(criteres['prix_max']):
                continue
            if criteres['surface_min'] and surface < int(criteres['surface_min']):
                continue
            if criteres['surface_max'] and surface > int(criteres['surface_max']):
                continue
                
            annonces_filtrees.append(annonce)
        except Exception as e:
            print(f"Erreur lors du filtrage d'une annonce : {str(e)}")
            continue
    
    print(f"Nombre d'annonces filtrées : {len(annonces_filtrees)}")
    
    # Ajout d'un délai artificiel de 1 seconde
    time.sleep(1)
    
    return jsonify([{
        'titre': a.titre,
        'prix': a.prix,
        'surface': a.surface,
        'localisation': a.localisation,
        'source': a.source,
        'url': a.url
    } for a in annonces_filtrees])

@app.route('/actualiser')
def actualiser():
    try:
        print("Début de l'actualisation des annonces")
        scrap_seloger()
        scrap_pap()
        print("Fin de l'actualisation des annonces")
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Erreur lors de l'actualisation : {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

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