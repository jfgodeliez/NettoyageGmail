#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Script de déploiement initial sur VPS Ubuntu
# Usage : bash deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DOMAIN="${YOUR_DOMAIN:-}"
EMAIL="${CERTBOT_EMAIL:-}"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Usage : YOUR_DOMAIN=gmail.mondomaine.com CERTBOT_EMAIL=toi@mail.com bash deploy.sh"
  exit 1
fi

echo "==> [1/6] Mise à jour système"
apt-get update -q && apt-get upgrade -y -q

echo "==> [2/6] Installation Docker"
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
fi

echo "==> [3/6] Configuration .env"
if [[ ! -f .env ]]; then
  cp .env.example .env
  sed -i "s/gmail.mondomaine.com/$DOMAIN/g" .env
  echo "   → .env créé. Ajoutez vos variables si nécessaire."
fi

echo "==> [4/6] Configuration Nginx (domaine)"
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" nginx/nginx.conf

echo "==> [5/6] Obtention certificat SSL Let's Encrypt"
# Démarrer nginx seul sur port 80 pour le challenge ACME
docker run --rm -d --name nginx-tmp \
  -p 80:80 \
  -v "$(pwd)/nginx/nginx-certbot-init.conf:/etc/nginx/nginx.conf:ro" \
  -v certbot_www:/var/www/certbot \
  nginx:alpine 2>/dev/null || true

docker run --rm \
  -v certbot_certs:/etc/letsencrypt \
  -v certbot_www:/var/www/certbot \
  certbot/certbot certonly --webroot \
    -w /var/www/certbot \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive

docker stop nginx-tmp 2>/dev/null || true

echo "==> [6/6] Build et démarrage des containers"
docker compose build --no-cache
docker compose up -d

echo ""
echo "✓ Déployé sur https://$DOMAIN"
echo "  Prochaine étape : copiez credentials.json dans ce répertoire, puis :"
echo "  docker compose restart app"
