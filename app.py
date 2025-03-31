from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_webdriver():
    """Initialize WebDriver following Railway's recommendations"""
    try:
        # Railway-specific configuration
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Use Railway's pre-installed Chrome
        chrome_options.binary_location = "/usr/bin/google-chrome-stable"
        
        # Initialize WebDriver with automatic driver management
        driver = webdriver.Chrome(
            service=Service(),
            options=chrome_options
        )
        logger.info("WebDriver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {str(e)}")
        raise

try:
    driver = init_webdriver()

except Exception as e:
    logger.error(f"Failed to initialize WebDriver: {str(e)}")
    # Fallback to basic driver if available
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("Fallback WebDriver initialized")
    except:
        logger.error("Could not initialize any WebDriver")
        raise

# Ensure driver is properly closed on app exit
import atexit
atexit.register(lambda: driver.quit() if 'driver' in locals() else None)
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
import requests
import re

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
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    # Use Railway's provided Chrome binary
    chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN', '/usr/bin/google-chrome')
    
    try:
        # Use Railway's ChromeDriver path
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
        service = Service(executable_path=chromedriver_path)
        
        # Verify ChromeDriver exists and is executable
        if not os.path.exists(chromedriver_path):
            raise FileNotFoundError(f"ChromeDriver not found at {chromedriver_path}")
        if not os.access(chromedriver_path, os.X_OK):
            os.chmod(chromedriver_path, 0o755)
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Successfully initialized ChromeDriver")
    except Exception as e:
        print(f"Failed to initialize ChromeDriver: {str(e)}")
        print("System information:")
        print(f"Chrome binary: {chrome_options.binary_location}")
        print(f"ChromeDriver path: {chromedriver_path}")
        print("Available binaries in /usr/bin/:")
        print(os.listdir('/usr/bin'))
        raise RuntimeError("Could not initialize Chrome WebDriver") from e
    
    try:
        villes = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille']
        for ville in villes:
            print(f"\nScraping de {ville} sur SeLoger")
            url = f'https://www.seloger.com/achat/immobilier/{ville}/'
            print(f"URL : {url}")
            
            try:
                driver.get(url)
                print("Page chargée avec Selenium")
                
                # Attendre que les annonces se chargent
                time.sleep(5)  # Attente pour le chargement JavaScript
                
                # Faire défiler la page pour charger plus d'annonces
                for _ in range(3):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                
                # Sauvegarder le HTML pour debug
                with open(f'seloger_{ville.lower()}.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print(f"HTML sauvegardé dans seloger_{ville.lower()}.html")
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Afficher les classes trouvées dans la page
                print("\nClasses trouvées dans la page :")
                for tag in soup.find_all(class_=True):
                    print(f"- {tag.get('class')}")
                
                # Essayer différents sélecteurs pour les annonces
                print("\nRecherche des annonces avec différents sélecteurs :")
                
                # Sélecteur 1 : data-test
                annonces = soup.find_all('div', {'data-test': 'sl.card-container'})
                print(f"Sélecteur data-test : {len(annonces)} annonces trouvées")
                
                # Sélecteur 2 : class c-pa-list
                if not annonces:
                    annonces = soup.find_all('div', class_='c-pa-list')
                    print(f"Sélecteur c-pa-list : {len(annonces)} annonces trouvées")
                
                # Sélecteur 3 : class c-pa-cpt
                if not annonces:
                    annonces = soup.find_all('div', class_='c-pa-cpt')
                    print(f"Sélecteur c-pa-cpt : {len(annonces)} annonces trouvées")
                
                # Sélecteur 4 : class c-pa
                if not annonces:
                    annonces = soup.find_all('div', class_='c-pa')
                    print(f"Sélecteur c-pa : {len(annonces)} annonces trouvées")
                
                # Sélecteur 5 : class sl.card-container
                if not annonces:
                    annonces = soup.find_all('div', class_='sl.card-container')
                    print(f"Sélecteur sl.card-container : {len(annonces)} annonces trouvées")
                
                # Sélecteur 6 : class sl.card
                if not annonces:
                    annonces = soup.find_all('div', class_='sl.card')
                    print(f"Sélecteur sl.card : {len(annonces)} annonces trouvées")
                
                print(f"\nNombre total d'annonces trouvées pour {ville}: {len(annonces)}")
                
                # Afficher le HTML de la première annonce si trouvée
                if annonces:
                    print("\nHTML de la première annonce :")
                    print(annonces[0].prettify())
                
                for i, annonce in enumerate(annonces, 1):
                    try:
                        print(f"\nTraitement de l'annonce {i}")
                        
                        # Essayer différents sélecteurs pour chaque champ
                        titre_elem = annonce.find('div', {'data-test': 'sl.card-title'}) or \
                                   annonce.find('h3', class_='c-pa-title') or \
                                   annonce.find('div', class_='c-pa-title') or \
                                   annonce.find('h2', class_='c-pa-title') or \
                                   annonce.find('div', class_='sl.card-title') or \
                                   annonce.find('h3', class_='sl.card-title')
                        
                        prix_elem = annonce.find('div', {'data-test': 'sl.card-price'}) or \
                                  annonce.find('div', class_='c-pa-price') or \
                                  annonce.find('span', class_='c-pa-price') or \
                                  annonce.find('div', class_='c-pa-criterion', string=lambda x: x and '€' in x) or \
                                  annonce.find('div', class_='sl.card-price') or \
                                  annonce.find('span', class_='sl.card-price')
                        
                        surface_elem = annonce.find('div', {'data-test': 'sl.card-surface'}) or \
                                     annonce.find('div', class_='c-pa-criterion', string=lambda x: x and 'm²' in x) or \
                                     annonce.find('span', class_='c-pa-criterion', string=lambda x: x and 'm²' in x) or \
                                     annonce.find('div', class_='sl.card-surface') or \
                                     annonce.find('span', class_='sl.card-surface')
                        
                        localisation_elem = annonce.find('div', {'data-test': 'sl.card-location'}) or \
                                          annonce.find('div', class_='c-pa-city') or \
                                          annonce.find('span', class_='c-pa-city') or \
                                          annonce.find('div', class_='c-pa-location') or \
                                          annonce.find('div', class_='sl.card-location') or \
                                          annonce.find('span', class_='sl.card-location')
                        
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
                
                time.sleep(random.uniform(2, 4))  # Délai entre les villes
                
            except Exception as e:
                print(f"Erreur lors du scraping de {ville} : {str(e)}")
                continue
        
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

def extraire_nombre(texte):
    """Extrait le premier nombre trouvé dans un texte."""
    match = re.search(r'(\d+(?:[.,]\d+)?)', texte)
    if match:
        return float(match.group(1).replace(',', '.'))
    return 0

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
    
    print(f"Recherche avec les paramètres : {criteres}")
    
    # Vérifier le nombre total d'annonces dans la base
    total_annonces = Annonce.query.count()
    print(f"Nombre total d'annonces dans la base : {total_annonces}")
    
    query = Annonce.query
    
    if criteres['localisation']:
        print(f"Recherche pour la localisation : {criteres['localisation']}")
        localisation = criteres['localisation'].lower()
        query = query.filter(
            db.or_(
                Annonce.localisation.ilike(f"%{localisation}%"),
                Annonce.localisation.ilike(f"%{localisation.capitalize()}%"),
                Annonce.localisation.ilike(f"%{localisation.upper()}%")
            )
        )
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
            prix = extraire_nombre(annonce.prix)
            print(f"Prix extrait pour {annonce.titre}: {prix}€")
            
            # Extraction de la surface numérique
            surface = extraire_nombre(annonce.surface)
            print(f"Surface extraite pour {annonce.titre}: {surface}m²")
            
            # Application des filtres
            if criteres['prix_min'] and prix < float(criteres['prix_min']):
                print(f"Filtré par prix min: {prix}€ < {criteres['prix_min']}€")
                continue
            if criteres['prix_max'] and prix > float(criteres['prix_max']):
                print(f"Filtré par prix max: {prix}€ > {criteres['prix_max']}€")
                continue
            if criteres['surface_min'] and surface < float(criteres['surface_min']):
                print(f"Filtré par surface min: {surface}m² < {criteres['surface_min']}m²")
                continue
            if criteres['surface_max'] and surface > float(criteres['surface_max']):
                print(f"Filtré par surface max: {surface}m² > {criteres['surface_max']}m²")
                continue
                
            annonces_filtrees.append(annonce)
            print(f"Annonce conservée après filtrage: {annonce.titre}")
        except Exception as e:
            print(f"Erreur lors du filtrage d'une annonce : {str(e)}")
            continue
    
    print(f"Nombre d'annonces filtrées : {len(annonces_filtrees)}")
    
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
        
        scrap_pap()
        print(f"Nombre d'annonces après PAP : {Annonce.query.count()}")
        
        scrap_seloger()
        print(f"Nombre d'annonces après SeLoger : {Annonce.query.count()}")
        
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
    print(f"Recherche de suggestions pour : {query}")
    
    if len(query) < 2:
        return jsonify([])
    
    # Liste des villes principales avec leurs variations
    villes = {
        "Paris": ["paris", "par"],
        "Lyon": ["lyon", "ly"],
        "Marseille": ["marseille", "mar"],
        "Bordeaux": ["bordeaux", "bord"],
        "Toulouse": ["toulouse", "toul"],
        "Nantes": ["nantes", "nant"],
        "Lille": ["lille", "lil"],
        "Rennes": ["rennes", "ren"],
        "Reims": ["reims", "rei"],
        "Le Havre": ["le havre", "havre", "hav"],
        "Saint-Étienne": ["saint-etienne", "saint etienne", "etienne"],
        "Toulon": ["toulon", "toul"],
        "Grenoble": ["grenoble", "gren"],
        "Dijon": ["dijon", "dij"],
        "Angers": ["angers", "ang"],
        "Nîmes": ["nimes", "nim"],
        "Villeurbanne": ["villeurbanne", "ville"],
        "Le Mans": ["le mans", "mans"],
        "Aix-en-Provence": ["aix-en-provence", "aix", "aix en provence"],
        "Brest": ["brest", "bre"],
        "Amiens": ["amiens", "ami"],
        "Limoges": ["limoges", "lim"],
        "Tours": ["tours", "tou"],
        "Clermont-Ferrand": ["clermont-ferrand", "clermont", "clerm"],
        "Rouen": ["rouen", "rou"],
        "Orléans": ["orleans", "orl"],
        "Metz": ["metz", "met"],
        "Caen": ["caen", "cae"],
        "Nancy": ["nancy", "nan"],
        "Saint-Denis": ["saint-denis", "saint denis", "denis"],
        "Argenteuil": ["argenteuil", "arg"],
        "Montreuil": ["montreuil", "mon"],
        "Roubaix": ["roubaix", "rou"],
        "Dunkerque": ["dunkerque", "dunk"],
        "Perpignan": ["perpignan", "per"],
        "Mulhouse": ["mulhouse", "mul"],
        "Nice": ["nice", "nic"],
        "Nanterre": ["nanterre", "nan"],
        "Courbevoie": ["courbevoie", "cour"],
        "Versailles": ["versailles", "ver"],
        "Créteil": ["creteil", "cre"],
        "Pau": ["pau", "pau"],
        "Poitiers": ["poitiers", "poi"],
        "La Rochelle": ["la rochelle", "rochelle", "roch"],
        "Angoulême": ["angouleme", "ang"],
        "Biarritz": ["biarritz", "bia"],
        "Bayonne": ["bayonne", "bay"],
        "Tarbes": ["tarbes", "tar"],
        "Montpellier": ["montpellier", "mon"],
        "Béziers": ["beziers", "bez"],
        "Sète": ["sete", "set"],
        "Avignon": ["avignon", "avi"],
        "Cannes": ["cannes", "can"],
        "Antibes": ["antibes", "ant"]
    }
    
    # Recherche des villes correspondantes
    suggestions = []
    for ville, variations in villes.items():
        if any(query in variation for variation in variations):
            suggestions.append(ville)
            if len(suggestions) >= 5:  # Limiter à 5 suggestions
                break
    
    print(f"Suggestions trouvées : {suggestions}")
    return jsonify(suggestions)

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