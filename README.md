# Agrégateur Immobilier

Une application web qui agrège les annonces immobilières de différents sites pour faciliter la recherche de biens immobiliers.

## Fonctionnalités

- Agrégation d'annonces immobilières depuis différents sites
- Recherche multicritères (prix, surface, localisation)
- Interface utilisateur moderne et responsive
- Actualisation automatique des annonces
- Base de données PostgreSQL pour le stockage des annonces

## Prérequis

- Python 3.8 ou supérieur
- Chrome WebDriver pour Selenium
- pip (gestionnaire de paquets Python)

## Installation locale

1. Clonez ce dépôt :
```bash
git clone [URL_DU_REPO]
cd immo-agregateur
```

2. Créez un environnement virtuel et activez-le :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Créez un fichier `.env` à la racine du projet :
```
DATABASE_URL=sqlite:///annonces.db
```

5. Lancez l'application :
```bash
python app.py
```

6. Ouvrez votre navigateur et accédez à :
```
http://localhost:5000
```

## Déploiement sur Railway

1. Créez un compte sur [Railway](https://railway.app/) et connectez-le à votre compte GitHub

2. Créez un nouveau projet sur Railway et sélectionnez ce dépôt

3. Ajoutez les variables d'environnement suivantes dans les paramètres du projet Railway :
   - `DATABASE_URL` : URL de la base de données PostgreSQL (fournie automatiquement par Railway)
   - `GOOGLE_CHROME_BIN` : Chemin vers l'exécutable Chrome
   - `CHROMEDRIVER_PATH` : Chemin vers ChromeDriver

4. Railway déploiera automatiquement votre application

## Structure du projet

- `app.py` : Application Flask principale
- `templates/index.html` : Interface utilisateur
- `requirements.txt` : Dépendances Python
- `Procfile` : Configuration pour Railway
- `.gitignore` : Fichiers à ignorer par Git

## Sites supportés

- SeLoger (plus de sites à venir)

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou à soumettre une pull request. 