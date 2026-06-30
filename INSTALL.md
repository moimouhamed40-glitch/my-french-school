# 🎓 École FLE — Guide d'installation complet

## Prérequis

| Outil | Version minimale |
|-------|-----------------|
| Python | 3.10+ |
| pip | 23+ |
| Redis | 7+ |
| Git | 2.30+ |
| (optionnel) PostgreSQL | 14+ |

---

## 1. Cloner et préparer le projet

```bash
git clone <votre-repo> my_french_school
cd my_french_school
```

---

## 2. Créer l'environnement virtuel

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Installer les dépendances Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Installer et démarrer Redis

### Windows
```bash
# Option 1 : WSL2 (recommandé)
wsl --install
wsl
sudo apt install redis-server
sudo service redis-server start

# Option 2 : Redis pour Windows
# Télécharger depuis : https://github.com/microsoftarchive/redis/releases
```

### macOS
```bash
brew install redis
brew services start redis
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y redis-server
sudo systemctl enable --now redis-server
```

### Vérification
```bash
redis-cli ping
# Doit retourner : PONG
```

---

## 5. Configurer les variables d'environnement

```bash
cp .env .env.local
```

Editez `.env` et remplissez :

```env
SECRET_KEY=une-cle-secrete-tres-longue-et-aleatoire
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI (obligatoire pour les fonctions IA)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx

# Agora SDK (pour le streaming vidéo)
AGORA_APP_ID=votre-agora-app-id
AGORA_APP_CERTIFICATE=votre-agora-certificate

# Email (optionnel en dev)
EMAIL_HOST_USER=votre-email@gmail.com
EMAIL_HOST_PASSWORD=votre-app-password
```

### Obtenir les clés API

**OpenAI :**
1. Allez sur https://platform.openai.com/api-keys
2. Créez une nouvelle clé API
3. Copiez dans `OPENAI_API_KEY`

**Agora SDK (streaming vidéo) :**
1. Créez un compte sur https://console.agora.io
2. Créez un projet → copiez l'App ID et le Certificate
3. Collez dans `AGORA_APP_ID` et `AGORA_APP_CERTIFICATE`

---

## 6. Installer le modèle français spaCy

```bash
python -m spacy download fr_core_news_md
# ou version légère :
python -m spacy download fr_core_news_sm
```

---

## 7. Migrations et base de données

```bash
# Créer les tables
python manage.py makemigrations accounts courses live_stream ai_tools
python manage.py migrate

# Créer un compte administrateur
python manage.py createsuperuser
```

---

## 8. Collecter les fichiers statiques

```bash
python manage.py collectstatic --noinput
```

---

## 9. Charger les données de démonstration (optionnel)

```bash
python manage.py loaddata fixtures/demo_data.json
```

Ou créez manuellement via l'admin Django :
- Allez sur http://localhost:8000/admin
- Ajoutez des catégories, cours, vidéos de formation IA, modèles de templates

---

## 10. Lancer le serveur de développement

### Option A : Daphne (ASGI — WebSockets actifs)
```bash
daphne -p 8000 my_french_school.asgi:application
```

### Option B : Django dev server (sans WebSockets)
```bash
python manage.py runserver
```

### Option C : Deux terminaux (recommandé en dev)
```bash
# Terminal 1 — Serveur ASGI
daphne -b 0.0.0.0 -p 8000 my_french_school.asgi:application

# Terminal 2 — Worker Celery (optionnel, pour tâches async)
celery -A my_french_school worker -l info
```

---

## 11. Accéder à la plateforme

| URL | Description |
|-----|-------------|
| http://localhost:8000/ | Page d'accueil |
| http://localhost:8000/admin/ | Interface d'administration |
| http://localhost:8000/accounts/register/ | Inscription |
| http://localhost:8000/courses/ | Liste des cours |
| http://localhost:8000/live/ | Sessions live |
| http://localhost:8000/ai/generator/ | Générateur d'exercices |
| http://localhost:8000/ai/chatbot/ | Chatbot FLE |
| http://localhost:8000/api/ | API REST |

---

## 12. Déploiement en production

### Variables d'environnement production
```env
DEBUG=False
SECRET_KEY=<cle-tres-securisee-256-bits>
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
DATABASE_URL=postgresql://user:password@localhost:5432/fle_db
REDIS_URL=redis://localhost:6379/0
```

### Avec Gunicorn + Nginx + Supervisor

```bash
# Installer gunicorn (déjà dans requirements.txt)
pip install gunicorn

# Lancer avec Daphne (ASGI pour WebSockets)
daphne -b 0.0.0.0 -p 8001 my_french_school.asgi:application

# Ou avec uvicorn
pip install uvicorn
uvicorn my_french_school.asgi:application --host 0.0.0.0 --port 8001 --workers 4
```

### Configuration Nginx (exemple)
```nginx
server {
    listen 80;
    server_name votre-domaine.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com;

    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;

    location /static/ { alias /var/www/fle/staticfiles/; }
    location /media/  { alias /var/www/fle/media/; }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 13. Structure des WebSockets

| URL WebSocket | Consumer | Usage |
|--------------|----------|-------|
| `ws/live/<session_uid>/` | LiveSessionConsumer | Chat, polls, whiteboard, présence |
| `ws/chatbot/<session_id>/` | ChatbotStreamConsumer | Streaming réponses IA |

---

## 14. API REST — Endpoints principaux

```
GET  /api/courses/              → Liste des cours publiés
GET  /api/courses/<id>/         → Détail d'un cours
GET  /api/courses/<id>/lessons/ → Leçons d'un cours
POST /api/courses/enroll/<id>/  → S'inscrire à un cours
GET  /api/courses/progress/     → Progression de l'utilisateur

POST /api/accounts/token/       → Obtenir un token d'auth
GET  /api/accounts/me/          → Profil utilisateur courant

GET  /api/live/sessions/        → Sessions live
POST /api/ai/generate/          → Générer des exercices IA
POST /api/ai/grammar/           → Correction grammaticale
POST /api/ai/chatbot/           → Chatbot (requête simple)
```

---

## 15. Tests

```bash
# Lancer tous les tests
python manage.py test

# Tester une app spécifique
python manage.py test apps.courses
python manage.py test apps.accounts

# Avec couverture de code
pip install coverage
coverage run manage.py test
coverage report
coverage html
```

---

## Dépannage courant

| Problème | Solution |
|----------|----------|
| `Redis connection refused` | Démarrer Redis : `sudo service redis-server start` |
| `Channel matching query does not exist` | Vérifier `CHANNEL_LAYERS` dans settings.py |
| `OpenAI API error` | Vérifier la clé API dans .env + crédit disponible |
| `spaCy model not found` | `python -m spacy download fr_core_news_md` |
| `Static files 404` | `python manage.py collectstatic` + vérifier STATICFILES_DIRS |
| `WebSocket 403` | Vérifier `AllowedHostsOriginValidator` dans asgi.py |
| Migrations manquantes | `python manage.py makemigrations && python manage.py migrate` |

---

## Structure du projet complète

```
my_french_school/
├── manage.py
├── requirements.txt
├── .env
├── INSTALL.md
│
├── my_french_school/          ← Configuration Django
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py                ← WebSocket + HTTP routing
│   └── wsgi.py
│
├── apps/
│   ├── accounts/              ← Utilisateurs, rôles, auth
│   ├── courses/               ← Cours, leçons, exercices, forum
│   ├── live_stream/           ← Sessions live, chat, polls, whiteboard
│   └── ai_tools/              ← Générateur IA, chatbot, correcteur
│
├── static/
│   ├── css/style.css          ← Styles personnalisés
│   ├── js/main.js             ← Widgets exercices, chatbot
│   └── js/live_stream.js      ← Agora RTC + WebSocket client
│
├── templates/
│   ├── base.html              ← Template maître bilingue fr/ar
│   ├── home.html              ← Page d'accueil
│   ├── accounts/              ← Login, register, dashboards
│   ├── courses/               ← Liste, détail, leçon, forum
│   ├── live_stream/           ← Salle live (room.html)
│   └── ai_tools/              ← Chatbot, générateur, correcteur
│
└── media/
    ├── stream_recordings/
    └── course_materials/
```

---

*Plateforme développée pour l'enseignement du français langue étrangère (FLE) — niveaux A1, A2, B1.*
