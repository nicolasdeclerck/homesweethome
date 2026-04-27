# CLAUDE.md — HomeSweetHome

## Vision du projet

**HomeSweetHome** est une application web qui aide les couples à répartir équitablement les charges ménagères, en prenant en compte la charge physique et mentale de chaque tâche.

Référence produit complète (parcours, user stories, stack) : https://www.notion.so/34f7cab116d380eb91e0f08437962abf

---

## Skills disponibles

Des skills custom sont disponibles dans `.claude/skills/`. Tu dois les utiliser systématiquement dans les contextes décrits ci-dessous.

### `create-github-issue`
**Déclencheur** : toute demande d'évolution ou de développement, sans exception.

C'est le point d'entrée systématique pour tout travail de développement. Le skill se charge lui-même de déterminer si un brainstorming préalable est nécessaire avant de créer l'issue. Ne pas créer d'issues GitHub manuellement sans passer par ce skill.

### `brainstorming`
**Déclencheur** : appelé par `create-github-issue` si nécessaire — ne pas l'invoquer directement.

### `implement-github-issue`
**Déclencheur** : uniquement si l'utilisateur demande explicitement de développer un ticket existant.

Ne pas l'utiliser de sa propre initiative. L'implémentation n'est lancée que sur instruction directe de l'utilisateur.

---

## Stack technique

### Backend
- **Django** — framework principal (vues, ORM, auth, sessions)
- **PostgreSQL** — base de données principale
- **Celery** — tâches asynchrones (envoi de mails d'invitation)
- **Redis** — broker Celery + cache Django

### Frontend
- **Django Templates** — rendu HTML côté serveur
- **HTMX** — interactions dynamiques sans rechargement de page
- **JS natif** — interactions légères complémentaires
- **WhiteNoise** — service des fichiers statiques en production

### Infrastructure
- **Docker / Docker Compose** — services : `web`, `db`, `redis`, `worker`
- **Traefik** — reverse proxy + TLS (déjà en place sur le VPS cible)
- **Service SMTP externe** (Brevo / Resend / Mailgun) — mails d'invitation

### CI / CD
- **GitHub Actions** — CI sur chaque PR, CD après merge sur `main`
- **ruff** — lint (étape 1 de la CI)
- **pytest + pytest-django + factory_boy** — tests (étape 2 de la CI)
- **coverage.py** — couverture cible : 80 %

---

## Conventions de développement

### Structure du projet

- Une app Django par domaine métier : `foyer`, `activites`, `evaluations`, `planification`
- Settings séparés par environnement : `config/settings/base.py`, `dev.py`, `test.py`, `prod.py`
- Tous les secrets via variables d'environnement — jamais de valeur en dur dans le code

### Modèles

- Toujours définir `__str__` sur chaque modèle
- Utiliser `verbose_name` et `verbose_name_plural`
- `ForeignKey` avec `on_delete=models.PROTECT` par défaut, sauf justification explicite
- Toujours créer et versionner les migrations après modification de modèles

### Vues & URLs

- Préférer les class-based views Django
- Nommer toutes les URLs (`name=`) — utiliser `{% url %}` dans les templates, jamais d'URL en dur
- Les endpoints HTMX retournent des fragments HTML partiels uniquement
- Toujours gérer le fallback non-HTMX (redirect) sur les vues mixtes
- Utiliser `HX-Trigger` pour les effets de bord (ex. mise à jour du total de charge)

### Celery

- Toutes les tâches doivent être **idempotentes**
- Utiliser `bind=True` + retry avec backoff exponentiel pour les tâches d'envoi de mail
- Ne jamais passer d'objets Django en argument — passer uniquement des IDs

### Tests

- Un test par comportement, pas par méthode
- `factory_boy` pour toutes les fixtures — pas de données en dur dans les tests
- Mocker Celery dans les tests d'intégration via `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)`
- Couverture minimale : **80 %** sur les apps métier

### Git & CI

- Branches nommées `feature/US-xxx-description` ou `fix/description`
- Chaque modification de code est rattachée à une issue GitHub
- Chaque PR doit passer lint (ruff) + tests (pytest) avant merge
- Ne jamais commiter de fichiers `.env` ou de secrets

---

## Commandes utiles

```bash
# Lancer l'environnement de dev
docker compose up -d

# Appliquer les migrations
docker compose exec web python manage.py migrate

# Lancer les tests
docker compose exec web pytest --cov=. --cov-report=term-missing -v

# Lancer le lint
docker compose exec web ruff check .

# Shell Django
docker compose exec web python manage.py shell
```
