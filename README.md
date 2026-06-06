# NettoyerGmail

Application web de nettoyage intelligent de boîte Gmail personnelle.

## Architecture

```
backend/   FastAPI (Python) — API REST + OAuth2 Gmail
frontend/  Vue.js 3 + Tailwind CSS — interface web
nginx/     Reverse proxy + SSL
docker-compose.yml
```

## Fonctionnement

1. Connexion OAuth2 Google (authentification sécurisée)
2. Analyse des métadonnées de tous vos emails (sans télécharger les corps)
3. Regroupement par thèmes : newsletters, e-commerce, réseaux sociaux, administratif…
4. Aperçu des emails dans un panneau latéral avant de décider
5. Actions en masse par groupe : conserver / archiver / supprimer
6. Exécution sécurisée avec mode dry-run

## Prérequis VPS

- Ubuntu 22.04+ avec Docker installé
- Un nom de domaine pointant vers le VPS (A record)
- Ports 80 et 443 ouverts
- Fichier `credentials.json` Google Cloud (voir ci-dessous)

## Configuration Google Cloud Console

1. [console.cloud.google.com](https://console.cloud.google.com) → créer/sélectionner un projet
2. **APIs & Services** → Bibliothèque → activer **Gmail API**
3. **Identifiants** → Créer → **ID client OAuth 2.0** → type **Application Web**
4. Authorized redirect URIs → ajouter : `https://VOTRE_DOMAINE/auth/callback`
5. Télécharger le JSON → renommer en `credentials.json` à la racine du projet
6. **Écran de consentement** → Utilisateurs test → ajouter votre adresse Gmail

## Déploiement VPS (première fois)

```bash
# Sur le VPS
git clone <repo> NettoyerGmail && cd NettoyerGmail

# Copier credentials.json depuis votre machine
scp credentials.json user@VPS:/chemin/NettoyerGmail/

# Lancer le déploiement automatique
YOUR_DOMAIN=gmail.mondomaine.com CERTBOT_EMAIL=toi@mail.com bash deploy.sh
```

## Mise à jour

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

## Tests

```bash
python -m venv venv_backend && venv_backend/Scripts/activate  # Windows
pip install -r backend/requirements.txt
pytest backend/tests/ -v
```

## Développement local

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (autre terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173 (proxy vers backend:8000)
```
