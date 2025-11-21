# Rapport technique — Application de Diagnostic Médical (CHU)

## Résumé exécutif

Ce document résume l'architecture, les fonctionnalités, les flux, la persistance et les recommandations de tests pour l'application de diagnostic médical développée en Python/Flask. Il sert de base pour le rapport de stage et contient les sections techniques, les scénarios de test et les recommandations opérationnelles.

## Architecture Générale

- Type : Application web monolithique (Flask + Jinja2) avec assets statiques (CSS/JS).
- Langages : Python (backend), HTML/Jinja (templates), CSS, JavaScript.
- Modèle ML : CatBoost chargé depuis `models/CatBoost_best_model.pkl`.
- Persistance : fichiers JSON sous `data/` (médecins, patients, activités, tokens).
- Génération PDF : `pdfkit` + `wkhtmltopdf` (binaire configurable via `WKHTMLTOPDF_CMD`).

## Composants Principaux

- `app.py` : point d'entrée Flask, routes, logique métier, intégration modèle, gestion sessions.
- `templates/` : vues Jinja — `base.html`, `index.html`, `result.html`, `admin_dashboard.html`, `pdf_template.html`, etc.
- `static/` : `style.css`, `admin_full.css`, `admin.js` (UI/admin interactivité).
- `models/disease_mapping.json` : mapping classe → nom maladie, examens, service.
- `data/medecins.json` : comptes médecins (id, mot de passe haché, rôle...).
- `data/patients.json` : historique des prédictions (nom, CIN, âge, sexe, maladie, médecin, service, date).

## Flux Utilisateur (haute-niveau)

1. Authentification : `/login` — validation via `doctors` (in-memory initialisé depuis `data/medecins.json`).
2. Diagnostic : formulaire patient → POST `/result` → DataFrame Pandas réordonné selon `model.feature_names_` → `model.predict` + `predict_proba` → mapping via `disease_mapping.json` → affichage `result.html` et persistance dans `data/patients.json`.
3. PDF : génération via `pdfkit.from_string()` en s'appuyant sur `pdf_template.html`.
4. Administration : `/admin` (protégé) — liste médecins, ajouter médecin (id auto-généré), toggle activation, reset mot de passe, activité et liste patients.

## Pages & Endpoints Clés

- `GET /login`, `POST /login`
- `GET /` (index)
- `POST /result` — lance la prédiction
- `POST /download-pdf` — retourne un PDF du diagnostic
- `GET /admin` — dashboard admin
- `POST /admin/add-doctor` — crée médecin (id auto-généré, hash mot de passe, signature et numéro d'ordre automatiques)
- `POST /admin/toggle-status` — activer/désactiver médecin
- `POST /admin/reset-password` — reset MDP
- `GET /api/admin/recent-activity` — JSON (admin only)

## Données et Format

- `data/medecins.json` : clé = username, valeur = { `id`, `password`, `nom_complet`, `specialite`, `numero_ordre`, `email`, `signature`, `role` }
- `data/patients.json` : liste d'objets { `nom`, `prenom`, `cin`, `age`, `sex`, `disease`, `doctor`, `service`, `date` }
- `models/disease_mapping.json` : map[class] → { `name`, `examens`, `service` }

Remarque : la correspondance des colonnes du DataFrame avec `model.feature_names_` est critique — respecter les noms (espaces inclus).

## Sécurité & Bonnes Pratiques

- Mots de passe : hachage via Werkzeug (`generate_password_hash`).
- Contrôles d'accès : `login_required` et `admin_required` décorateurs.
- Limitations actuelles : pas de protection CSRF, stockage JSON non-concurrent-safe, pas de contrôle de rôle fin.

Recommandations : ajouter CSRF (Flask-WTF), migrer vers une base de données (SQLite/Postgres), ajouter journalisation des actions critiques.

## Tests recommandés

- Tests manuels : login (valide/invalide), forgot/reset password, prédiction (valeurs normales / extrêmes), génération PDF, ajout médecin, toggle, visualiser patients.
- Tests automatisés : `pytest` + fixtures Flask `app.test_client()` ; mock du modèle pour tests unitaires (ex. remplacer `model.predict` par stub).
- Scénario important : vérifier comportement si `models/CatBoost_best_model.pkl` manquant et si `wkhtmltopdf` absent.

## Limitations & Améliorations futures

- Passage à une base de données relationnelle pour concurrence et intégrité.
- Ajout de CSRF et durcissement des validations côté serveur.
- Tests CI/CD et vérification automatique du modèle avant déploiement.
- UI : pagination et recherche sur la table patients, export CSV.

## Annexes — exemples rapides

- Lancer l'application en local :
```
; .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```
- Générer le rapport (voir `generate_report.ps1` fourni) : utilise `pandoc`/`wkhtmltopdf` si installés.

---
_Fichier généré automatiquement par l'assistant — modifiez-le si nécessaire pour votre rapport de stage._
