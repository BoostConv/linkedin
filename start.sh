#!/bin/bash
set -e

echo "🚀 LinkedIn Automation — Démarrage"
echo "=================================="

# Check .env
if [ ! -f backend/.env ]; then
    echo "📋 Création du fichier .env depuis .env.example..."
    cp backend/.env.example backend/.env
    echo "⚠️  Pensez à remplir vos clés API dans backend/.env"
    echo "   - ANTHROPIC_API_KEY (obligatoire pour la génération)"
    echo "   - LINKEDIN_CLIENT_ID + LINKEDIN_CLIENT_SECRET (pour la publication)"
    echo "   - OPENAI_API_KEY (pour les visuels DALL-E)"
    echo ""
fi

# Build & start
echo "🐳 Build et démarrage des conteneurs..."
docker compose up -d --build

# Wait for backend to be healthy
echo "⏳ Attente que le backend soit prêt..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✅ Backend prêt !"
        break
    fi
    sleep 2
done

# Run migrations
echo "🗄️  Exécution des migrations..."
docker compose exec backend alembic upgrade head

# Seed data
echo "🌱 Initialisation des données (piliers, templates, règles)..."
docker compose exec backend python -c "
import asyncio
from app.seed import seed_all
asyncio.run(seed_all())
print('Seed terminé !')
"

echo ""
echo "=================================="
echo "✅ LinkedIn Automation est lancé !"
echo ""
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/api/docs"
echo ""
echo "   1. Créez un compte sur le frontend"
echo "   2. Connectez votre LinkedIn dans Réglages"
echo "   3. Générez votre premier post !"
echo "=================================="
