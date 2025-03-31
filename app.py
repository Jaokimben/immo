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
import random

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
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"\nScraping de {ville} sur SeLoger")
            url = f'https://www.seloger.com/achat/immobilier/{ville}/'
            print(f"URL : {url}")
            driver.get(url)
            time.sleep(random.uniform(2, 4))  # Délai aléatoire
            
            # Attendre que la page soit chargée
            driver.implicitly_wait(10)
            
            # Sauvegarder le HTML pour debug
            with open(f'seloger_{ville.lower()}.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"HTML sauvegardé dans seloger_{ville.lower()}.html")
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Essayer différents sélecteurs pour les annonces
            annonces = soup.find_all('div', {'data-test': 'sl.card-container'})
            if not annonces:
                print("Sélecteur data-test non trouvé, essai avec c-pa-list")
                annonces = soup.find_all('div', class_='c-pa-list')
            if not annonces:
                print("Sélecteur c-pa-list non trouvé, essai avec c-pa-cpt")
                annonces = soup.find_all('div', class_='c-pa-cpt')
            if not annonces:
                print("Sélecteur c-pa-cpt non trouvé, essai avec c-pa")
                annonces = soup.find_all('div', class_='c-pa')
            
            print(f"Nombre d'annonces trouvées pour {ville}: {len(annonces)}")
            
            for i, annonce in enumerate(annonces, 1):
                try:
                    print(f"\nTraitement de l'annonce {i}")
                    
                    # Essayer différents sélecteurs pour chaque champ
                    titre_elem = annonce.find('div', {'data-test': 'sl.card-title'}) or \
                               annonce.find('h3', class_='c-pa-title') or \
                               annonce.find('div', class_='c-pa-title') or \
                               annonce.find('h2', class_='c-pa-title')
                    
                    prix_elem = annonce.find('div', {'data-test': 'sl.card-price'}) or \
                              annonce.find('div', class_='c-pa-price') or \
                              annonce.find('span', class_='c-pa-price') or \
                              annonce.find('div', class_='c-pa-criterion', string=lambda x: x and '€' in x)
                    
                    surface_elem = annonce.find('div', {'data-test': 'sl.card-surface'}) or \
                                 annonce.find('div', class_='c-pa-criterion', string=lambda x: x and 'm²' in x) or \
                                 annonce.find('span', class_='c-pa-criterion', string=lambda x: x and 'm²' in x)
                    
                    localisation_elem = annonce.find('div', {'data-test': 'sl.card-location'}) or \
                                      annonce.find('div', class_='c-pa-city') or \
                                      annonce.find('span', class_='c-pa-city') or \
                                      annonce.find('div', class_='c-pa-location')
                    
                    if not all([titre_elem, prix_elem, surface_elem, localisation_elem]):
                        print("Éléments manquants pour cette annonce")
                        print(f"Titre: {bool(titre_elem)}")
                        print(f"Prix: {bool(prix_elem)}")
                        print(f"Surface: {bool(surface_elem)}")
                        print(f"Localisation: {bool(localisation_elem)}")
                        continue
                    
                    titre = titre_elem.text.strip()
                    prix = prix_elem.text.strip()
                    surface = surface_elem.text.strip()
                    localisation = localisation_elem.text.strip()
                    
                    print(f"Annonce trouvée :")
                    print(f"- Titre : {titre}")
                    print(f"- Prix : {prix}")
                    print(f"- Surface : {surface}")
                    print(f"- Localisation : {localisation}")
                    
                    # Vérifier si l'annonce existe déjà
                    if not Annonce.query.filter_by(titre=titre, source='SeLoger').first():
                        nouvelle_annonce = Annonce(
                            titre=titre,
                            prix=prix,
                            surface=surface,
                            localisation=localisation,
                            source='SeLoger',
                            url=annonce.find('a')['href'] if annonce.find('a') else ''
                        )
                        db.session.add(nouvelle_annonce)
                        print("Nouvelle annonce ajoutée à la base de données")
                    else:
                        print("Annonce déjà existante, ignorée")
                except Exception as e:
                    print(f"Erreur lors du traitement d'une annonce SeLoger : {str(e)}")
                    continue
            
            time.sleep(random.uniform(1, 3))  # Délai entre les villes
        
        db.session.commit()
        print("\nFin du scraping SeLoger")
        print(f"Nombre total d'annonces dans la base : {Annonce.query.count()}")
    
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
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"Scraping de {ville} sur PAP")
            url = f'https://www.pap.fr/annonce/achat-immobilier-{ville.lower()}'
            driver.get(url)
            time.sleep(random.uniform(2, 4))  # Délai aléatoire
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
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
            
            time.sleep(random.uniform(1, 3))  # Délai entre les villes
        
        db.session.commit()
        print("Fin du scraping PAP")
    
    except Exception as e:
        print(f"Erreur lors du scraping PAP : {str(e)}")
    finally:
        driver.quit()

def scrap_leboncoin():
    print("Début du scraping LeBonCoin")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"Scraping de {ville} sur LeBonCoin")
            url = f'https://www.leboncoin.fr/recherche?category=9&locations={ville}'
            driver.get(url)
            time.sleep(random.uniform(2, 4))  # Délai aléatoire
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            annonces = soup.find_all('div', class_='styles_adCard')
            
            for annonce in annonces:
                try:
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
                        print(f"Nouvelle annonce ajoutée : {titre}")
                except Exception as e:
                    print(f"Erreur lors du traitement d'une annonce LeBonCoin : {str(e)}")
                    continue
            
            time.sleep(random.uniform(1, 3))  # Délai entre les villes
        
        db.session.commit()
        print("Fin du scraping LeBonCoin")
    
    except Exception as e:
        print(f"Erreur lors du scraping LeBonCoin : {str(e)}")
    finally:
        driver.quit()

def scrap_orpi():
    print("Début du scraping Orpi")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"Scraping de {ville} sur Orpi")
            url = f'https://www.orpi.com/recherche/achat-immobilier-{ville.lower()}'
            driver.get(url)
            time.sleep(random.uniform(2, 4))  # Délai aléatoire
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            annonces = soup.find_all('div', class_='property-card')
            
            for annonce in annonces:
                try:
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
                        print(f"Nouvelle annonce ajoutée : {titre}")
                except Exception as e:
                    print(f"Erreur lors du traitement d'une annonce Orpi : {str(e)}")
                    continue
            
            time.sleep(random.uniform(1, 3))  # Délai entre les villes
        
        db.session.commit()
        print("Fin du scraping Orpi")
    
    except Exception as e:
        print(f"Erreur lors du scraping Orpi : {str(e)}")
    finally:
        driver.quit()

def scrap_logicimmo():
    print("Début du scraping Logic-Immo")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"Scraping de {ville} sur Logic-Immo")
            url = f'https://www.logic-immo.com/achat-immobilier-{ville.lower()}'
            driver.get(url)
            time.sleep(random.uniform(2, 4))  # Délai aléatoire
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            annonces = soup.find_all('div', class_='announcement-card')
            
            for annonce in annonces:
                try:
                    titre = annonce.find('h3', class_='announcement-title').text.strip()
                    prix = annonce.find('div', class_='announcement-price').text.strip()
                    surface = annonce.find('div', class_='announcement-surface').text.strip()
                    localisation = annonce.find('div', class_='announcement-location').text.strip()
                    
                    if not Annonce.query.filter_by(titre=titre, source='Logic-Immo').first():
                        nouvelle_annonce = Annonce(
                            titre=titre,
                            prix=prix,
                            surface=surface,
                            localisation=localisation,
                            source='Logic-Immo',
                            url=annonce.find('a')['href']
                        )
                        db.session.add(nouvelle_annonce)
                        print(f"Nouvelle annonce ajoutée : {titre}")
                except Exception as e:
                    print(f"Erreur lors du traitement d'une annonce Logic-Immo : {str(e)}")
                    continue
            
            time.sleep(random.uniform(1, 3))  # Délai entre les villes
        
        db.session.commit()
        print("Fin du scraping Logic-Immo")
    
    except Exception as e:
        print(f"Erreur lors du scraping Logic-Immo : {str(e)}")
    finally:
        driver.quit()

def scrap_century21():
    print("Début du scraping Century 21")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"Scraping de {ville} sur Century 21")
            url = f'https://www.century21.fr/achat/immobilier-{ville.lower()}'
            driver.get(url)
            time.sleep(random.uniform(2, 4))  # Délai aléatoire
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            annonces = soup.find_all('div', class_='property-card')
            
            for annonce in annonces:
                try:
                    titre = annonce.find('h2', class_='property-title').text.strip()
                    prix = annonce.find('div', class_='property-price').text.strip()
                    surface = annonce.find('div', class_='property-surface').text.strip()
                    localisation = annonce.find('div', class_='property-location').text.strip()
                    
                    if not Annonce.query.filter_by(titre=titre, source='Century 21').first():
                        nouvelle_annonce = Annonce(
                            titre=titre,
                            prix=prix,
                            surface=surface,
                            localisation=localisation,
                            source='Century 21',
                            url=annonce.find('a')['href']
                        )
                        db.session.add(nouvelle_annonce)
                        print(f"Nouvelle annonce ajoutée : {titre}")
                except Exception as e:
                    print(f"Erreur lors du traitement d'une annonce Century 21 : {str(e)}")
                    continue
            
            time.sleep(random.uniform(1, 3))  # Délai entre les villes
        
        db.session.commit()
        print("Fin du scraping Century 21")
    
    except Exception as e:
        print(f"Erreur lors du scraping Century 21 : {str(e)}")
    finally:
        driver.quit()

def scrap_nexity():
    print("Début du scraping Nexity")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"Scraping de {ville} sur Nexity")
            url = f'https://www.nexity.fr/achat/immobilier-{ville.lower()}'
            driver.get(url)
            time.sleep(random.uniform(2, 4))  # Délai aléatoire
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            annonces = soup.find_all('div', class_='property-card')
            
            for annonce in annonces:
                try:
                    titre = annonce.find('h2', class_='property-title').text.strip()
                    prix = annonce.find('div', class_='property-price').text.strip()
                    surface = annonce.find('div', class_='property-surface').text.strip()
                    localisation = annonce.find('div', class_='property-location').text.strip()
                    
                    if not Annonce.query.filter_by(titre=titre, source='Nexity').first():
                        nouvelle_annonce = Annonce(
                            titre=titre,
                            prix=prix,
                            surface=surface,
                            localisation=localisation,
                            source='Nexity',
                            url=annonce.find('a')['href']
                        )
                        db.session.add(nouvelle_annonce)
                        print(f"Nouvelle annonce ajoutée : {titre}")
                except Exception as e:
                    print(f"Erreur lors du traitement d'une annonce Nexity : {str(e)}")
                    continue
            
            time.sleep(random.uniform(1, 3))  # Délai entre les villes
        
        db.session.commit()
        print("Fin du scraping Nexity")
    
    except Exception as e:
        print(f"Erreur lors du scraping Nexity : {str(e)}")
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
    
    # Vérifier le nombre total d'annonces dans la base
    total_annonces = Annonce.query.count()
    print(f"Nombre total d'annonces dans la base : {total_annonces}")
    
    query = Annonce.query
    
    if criteres['localisation']:
        print(f"Recherche pour la localisation : {criteres['localisation']}")
        query = query.filter(
            db.or_(
                Annonce.localisation.ilike(f"%{criteres['localisation']}%"),
                Annonce.localisation.ilike(f"%{criteres['localisation'].capitalize()}%"),
                Annonce.localisation.ilike(f"%{criteres['localisation'].upper()}%")
            )
        )
        # Afficher la requête SQL générée
        print(f"Requête SQL : {query}")
    
    annonces = query.order_by(Annonce.date_ajout.desc()).all()
    print(f"Nombre d'annonces trouvées : {len(annonces)}")
    
    # Afficher les premières annonces trouvées
    for i, annonce in enumerate(annonces[:5]):
        print(f"Annonce {i+1}: {annonce.titre} - {annonce.localisation}")
    
    # Filtrage des annonces en fonction des critères numériques
    annonces_filtrees = []
    for annonce in annonces:
        try:
            # Extraction du prix numérique
            prix_str = ''.join(filter(str.isdigit, annonce.prix))
            prix = int(prix_str) if prix_str else 0
            print(f"Prix extrait pour {annonce.titre}: {prix}")
            
            # Extraction de la surface numérique
            surface_str = ''.join(filter(str.isdigit, annonce.surface))
            surface = int(surface_str) if surface_str else 0
            print(f"Surface extraite pour {annonce.titre}: {surface}")
            
            # Application des filtres
            if criteres['prix_min'] and prix < int(criteres['prix_min']):
                print(f"Filtré par prix min: {prix} < {criteres['prix_min']}")
                continue
            if criteres['prix_max'] and prix > int(criteres['prix_max']):
                print(f"Filtré par prix max: {prix} > {criteres['prix_max']}")
                continue
            if criteres['surface_min'] and surface < int(criteres['surface_min']):
                print(f"Filtré par surface min: {surface} < {criteres['surface_min']}")
                continue
            if criteres['surface_max'] and surface > int(criteres['surface_max']):
                print(f"Filtré par surface max: {surface} > {criteres['surface_max']}")
                continue
                
            annonces_filtrees.append(annonce)
            print(f"Annonce conservée après filtrage: {annonce.titre}")
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
        print(f"Nombre d'annonces avant actualisation : {Annonce.query.count()}")
        
        scrap_seloger()
        print(f"Nombre d'annonces après SeLoger : {Annonce.query.count()}")
        
        scrap_pap()
        print(f"Nombre d'annonces après PAP : {Annonce.query.count()}")
        
        scrap_leboncoin()
        print(f"Nombre d'annonces après LeBonCoin : {Annonce.query.count()}")
        
        scrap_orpi()
        print(f"Nombre d'annonces après Orpi : {Annonce.query.count()}")
        
        scrap_logicimmo()
        print(f"Nombre d'annonces après Logic-Immo : {Annonce.query.count()}")
        
        scrap_century21()
        print(f"Nombre d'annonces après Century 21 : {Annonce.query.count()}")
        
        scrap_nexity()
        print(f"Nombre d'annonces après Nexity : {Annonce.query.count()}")
        
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

@app.route('/test_scraping')
def test_scraping():
    try:
        print("Début du test de scraping")
        print(f"Nombre d'annonces avant test : {Annonce.query.count()}")
        
        # Test avec SeLoger uniquement
        scrap_seloger()
        
        print(f"Nombre d'annonces après test : {Annonce.query.count()}")
        return jsonify({
            'status': 'success',
            'message': 'Test de scraping terminé',
            'annonces_avant': Annonce.query.count()
        })
    except Exception as e:
        print(f"Erreur lors du test de scraping : {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/test_seloger')
def test_seloger():
    try:
        print("Début du test de scraping SeLoger")
        print(f"Nombre d'annonces avant test : {Annonce.query.count()}")
        
        # Test avec SeLoger uniquement
        scrap_seloger()
        
        print(f"Nombre d'annonces après test : {Annonce.query.count()}")
        return jsonify({
            'status': 'success',
            'message': 'Test de scraping SeLoger terminé',
            'annonces_avant': Annonce.query.count()
        })
    except Exception as e:
        print(f"Erreur lors du test de scraping SeLoger : {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 