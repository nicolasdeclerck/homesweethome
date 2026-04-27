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
- **CD** (`.github/workflows/cd.yml`) — déclenché sur push `main` : build de
  l'image Docker et push vers `ghcr.io/nicolasdeclerck/homesweethome`.
  L'étape de déploiement sur le VPS est en placeholder (voir « À paramétrer »
  ci-dessous).

## À paramétrer manuellement

Ce que la stack ne peut pas configurer toute seule et qui doit être fait par
l'utilisateur :

### GitHub
- **Permissions GHCR** : vérifier dans
  *Settings → Actions → General → Workflow permissions* que `Read and write`
  est activé (nécessaire pour pousser sur GHCR avec le `GITHUB_TOKEN`
  automatique).
- **Visibilité de l'image** : après le premier push, l'image sera privée par
  défaut sur GHCR. La rendre publique (si souhaité) depuis l'onglet *Packages*
  du repo.

### Service SMTP de production
Choisir un fournisseur (Brevo / Resend / Mailgun) et créer le compte. Reporter
les credentials dans les variables d'environnement de l'hôte de prod :
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`.

### Hébergement (VPS Traefik)
- **Secrets GitHub à ajouter** quand le VPS sera prêt (pour câbler le job
  `deploy` du workflow CD) :
  - `DEPLOY_SSH_KEY` — clé privée SSH du déploiement
  - `DEPLOY_HOST` — hostname du VPS
  - `DEPLOY_USER` — utilisateur SSH
- **Variables d'environnement à set sur le VPS** :
  - `DJANGO_SETTINGS_MODULE=config.settings.prod`
  - `DJANGO_SECRET_KEY` (regénérée, ≥ 50 caractères)
  - `DJANGO_ALLOWED_HOSTS` (le domaine cible)
  - `POSTGRES_*`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
  - `EMAIL_*` (cf. section SMTP)
- **Labels Traefik** : à ajouter sur le service `web` dans le compose de prod
  une fois le domaine connu.
- **Job `deploy`** : décommenter et compléter dans `.github/workflows/cd.yml`
  une fois les secrets ci-dessus disponibles.

## Conventions

- Branches : `feature/<issue>-description` ou `fix/<issue>-description`
- Une issue GitHub par évolution (passer par le skill `create-github-issue`)
- Tests : un test par comportement, factory_boy pour les fixtures, mocker
  Celery via `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)`
- ForeignKey : `on_delete=models.PROTECT` par défaut
- Tâches Celery : idempotentes, ne reçoivent que des IDs en argument
