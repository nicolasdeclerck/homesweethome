# HomeSweetHome

Application web qui aide les couples à répartir équitablement les charges
ménagères, en prenant en compte la charge physique et mentale de chaque tâche.

## Stack technique

- **Backend** : Django 5.1, PostgreSQL 16, Celery 5, Redis 7
- **Frontend** : Django Templates + HTMX
- **Infra** : Docker Compose (services `web`, `db`, `redis`, `worker`)
- **Qualité** : ruff, pytest, pytest-django, factory_boy, coverage ≥ 80 %
- **CI/CD** : GitHub Actions → image Docker poussée sur GHCR

## Prérequis

- Docker + Docker Compose
- Make optionnel (pas requis)
- Python 3.12 si tu veux lancer des outils en dehors du conteneur

## Démarrage rapide

```bash
# 1. Cloner et entrer dans le repo
git clone git@github.com:nicolasdeclerck/homesweethome.git
cd homesweethome

# 2. Créer le fichier d'environnement local
cp .env.example .env
# (Édite .env si besoin — les valeurs par défaut suffisent pour le dev)

# 3. Lancer les services
docker compose up -d --build

# 4. Appliquer les migrations
docker compose exec web python manage.py migrate

# 5. (Optionnel) Créer un superuser pour l'admin Django
docker compose exec web python manage.py createsuperuser

# 6. Vérifier que tout passe
docker compose exec web python manage.py check
docker compose exec web ruff check .
docker compose exec web pytest --cov=. --cov-report=term-missing -v
```

L'application est ensuite disponible sur <http://localhost:8000>, l'admin sur
<http://localhost:8000/admin/>.

## Commandes utiles

```bash
# Logs d'un service
docker compose logs -f web

# Shell Django
docker compose exec web python manage.py shell

# Créer une migration
docker compose exec web python manage.py makemigrations

# Lancer le worker Celery manuellement
docker compose exec worker celery -A config worker --loglevel=info

# Stopper et tout nettoyer (⚠️ supprime les volumes Postgres / Redis)
docker compose down -v
```

## Structure du projet

```
homesweethome/
├── config/                 # projet Django (settings split, celery, urls)
├── foyer/                  # domaine : foyers, invitations, membres
├── activites/              # domaine : tâches ménagères et leurs charges
├── evaluations/            # domaine : évaluation de la charge mentale/physique
├── planification/          # domaine : répartition et planning
├── templates/              # templates partagés (layout HTMX)
├── requirements/           # dépendances par environnement
├── .github/workflows/      # CI (PR) et CD (merge main)
├── Dockerfile              # multi-stage (builder → runtime gunicorn)
├── docker-compose.yml      # web, db, redis, worker
├── pyproject.toml          # ruff + pytest + coverage
└── manage.py
```

## Settings par environnement

Le projet utilise un module de settings dédié par environnement :

| Module                   | Quand l'utiliser                            |
| ------------------------ | ------------------------------------------- |
| `config.settings.dev`    | Dev local (DEBUG, mails console)            |
| `config.settings.test`   | Pytest (SQLite mémoire, Celery EAGER)       |
| `config.settings.prod`   | Production (HSTS, cookies sécurisés, SMTP)  |

Le fichier de settings actif est piloté par la variable d'environnement
`DJANGO_SETTINGS_MODULE`.

## CI / CD

- **CI** (`.github/workflows/ci.yml`) — déclenché sur PR et push `main` :
  étape `lint` (ruff) puis `tests` (pytest + coverage avec gate 80 %).
  Postgres et Redis tournent en services Actions.
- **CD** (`.github/workflows/cd.yml`) — déclenché sur push `main` :
  1. **build-and-push** : build de l'image Docker et push vers
     `ghcr.io/nicolasdeclerck/homesweethome`.
  2. **deploy** : SSH sur le VPS et exécution de la séquence de
     déploiement (cf. section *Déploiement* ci-dessous). Nécessite les
     secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` (cf. *À
     paramétrer*).

## Déploiement

### Premier déploiement (manuel sur VPS)

Sur un VPS qui héberge déjà Traefik (réseau Docker partagé
`n8n-traefik_default`) :

```bash
cd /home/ubuntu/n8n-traefik/repos/
git clone -b main git@github.com:nicolasdeclerck/homesweethome.git
cd homesweethome

# Préparer .env.prod à partir du template
cp .env.prod.example .env.prod
# Générer SECRET_KEY et POSTGRES_PASSWORD :
#   python3 -c 'import secrets; print(secrets.token_urlsafe(60))'
#   openssl rand -base64 32 | tr -d '/+='
# puis éditer .env.prod

# Build local pour le tout premier setup (avant que GHCR ait la première image)
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Initialiser Django
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml restart web   # recharger le manifest WhiteNoise
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### Déploiements suivants

Tout est automatisé par le workflow CD : à chaque merge sur `main`, l'image
est buildée, pushée sur GHCR, puis le runner SSH sur le VPS et exécute la
séquence. La séquence reproduite manuellement, en cas de besoin :

```bash
cd /home/ubuntu/n8n-traefik/repos/homesweethome
git fetch origin main && git checkout main && git reset --hard origin/main
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --no-build --remove-orphans
docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml restart web
docker image prune -f
```

> **Pourquoi `restart web` après `collectstatic`** : avec
> `whitenoise.storage.CompressedManifestStaticFilesStorage`, Django charge
> `staticfiles.json` en mémoire au démarrage. Si on `collectstatic` sur un
> processus déjà démarré, le manifest mémoire est désynchronisé du disque
> et les URLs `{% static %}` perdent leur hash → 404 sur les CSS/JS.

## À paramétrer manuellement

Ce que la stack ne peut pas configurer toute seule et qui doit être fait par
l'utilisateur :

### GitHub
- **Permissions Workflows** : *Settings → Actions → General → Workflow
  permissions* → activer *Read and write* (nécessaire pour pousser sur
  GHCR avec le `GITHUB_TOKEN` automatique).
- **Visibilité de l'image GHCR** : après le premier push, l'image est
  privée par défaut. La rendre publique depuis l'onglet *Packages* du
  repo si tu ne veux pas avoir à `docker login` sur le VPS.
- **Secrets pour le déploiement automatique** : *Settings → Secrets and
  variables → Actions* → ajouter :
  - `DEPLOY_HOST` — IP publique ou hostname du VPS
  - `DEPLOY_USER` — utilisateur SSH (ex. `ubuntu`)
  - `DEPLOY_SSH_KEY` — clé SSH privée **dédiée au déploiement** (sans
    passphrase). La clé publique correspondante doit être ajoutée dans
    `~/.ssh/authorized_keys` du `DEPLOY_USER` sur le VPS.

### Service SMTP de production
Choisir un fournisseur (Brevo / Resend / Mailgun) et créer le compte.
Reporter les credentials dans `.env.prod` du VPS : `EMAIL_HOST`,
`EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`,
`DEFAULT_FROM_EMAIL`.

### VPS
- **Variables d'environnement** dans `.env.prod` (cf. `.env.prod.example`).
- **DNS** : un record A/CNAME doit pointer le domaine cible vers l'IP
  publique du VPS *avant* le premier `up -d` (sinon Let's Encrypt ne peut
  pas valider).

## Conventions

- Branches : `feature/<issue>-description` ou `fix/<issue>-description`
- Une issue GitHub par évolution (passer par le skill `create-github-issue`)
- Tests : un test par comportement, factory_boy pour les fixtures, mocker
  Celery via `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)`
- ForeignKey : `on_delete=models.PROTECT` par défaut
- Tâches Celery : idempotentes, ne reçoivent que des IDs en argument
