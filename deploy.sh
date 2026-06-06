#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Script de déploiement initial sur VPS Ubuntu
# Usage : YOUR_DOMAIN=gmail.mondomaine.com CERTBOT_EMAIL=toi@mail.com bash deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DOMAIN="${YOUR_DOMAIN:-}"
EMAIL="${CERTBOT_EMAIL:-}"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Usage : YOUR_DOMAIN=gmail.mondomaine.com CERTBOT_EMAIL=toi@mail.com bash deploy.sh"
  exit 1
fi

SUDO=""
if [[ $EUID -ne 0 ]]; then
  SUDO="sudo"
fi

echo "==> [1/6] Mise à jour système"
$SUDO apt-get update -q && $SUDO apt-get upgrade -y -q

echo "==> [2/6] Installation Docker"
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | $SUDO sh
  $SUDO systemctl enable docker
  $SUDO systemctl start docker
  # Permettre à l'utilisateur courant d'utiliser docker sans sudo
  $SUDO usermod -aG docker "$USER"
  echo "   → Docker installé. Reconnectez-vous si les commandes docker échouent."
fi

echo "==> [3/6] Configuration .env"
if [[ ! -f .env ]]; then
  cp .env.example .env
  sed -i "s/gmail.mondomaine.com/$DOMAIN/g" .env
  echo "   → .env créé."
fi

echo "==> [4/6] Configuration Nginx (domaine)"
# Remplacer seulement si pas encore fait
if grep -q "YOUR_DOMAIN" nginx/nginx.conf; then
  sed -i "s/YOUR_DOMAIN/$DOMAIN/g" nginx/nginx.conf
fi

echo "==> [5/6] Obtention certificat SSL Let's Encrypt (mode standalone)"
# Standalone : certbot ouvre lui-même le port 80, pas besoin de nginx intermédiaire
docker run --rm \
  -p 80:80 \
  -v certbot_certs:/etc/letsencrypt \
  certbot/certbot certonly --standalone \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive

echo "==> [6/6] Build et démarrage des containers"
docker compose build --no-cache
docker compose up -d

echo ""
echo "✓ Déployé sur https://$DOMAIN"
echo ""
echo "Prochaine étape :"
echo "  1. Copier credentials.json dans ce répertoire"
echo "  2. docker compose restart app"
