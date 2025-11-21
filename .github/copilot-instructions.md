## Purpose
Short guidance for AI coding agents to be productive in this repository.

## Big picture
- **Flask web app**: single-process Flask app in `app.py` that serves HTML templates under `templates/` and static assets under `static/`.
- **ML model**: a CatBoost model is expected at `models/CatBoost_best_model.pkl`. Predictions happen in `/result` by building a pandas DataFrame whose columns must match `model.feature_names_`.
- **Data & mappings**: disease metadata lives in `models/disease_mapping.json`. Doctor accounts are stored both as an in-memory `doctors` dict in `app.py` and in `data/medecins.json` (used by `admin_required`).

## Key files to read first
- `app.py` — main entrypoint and the majority of app logic (auth, routes, PDF generation, prediction flow).
- `README.md` — project overview and dev/run steps (has system requirements like wkhtmltopdf and Python version).
- `models/disease_mapping.json` — authoritative disease -> exams/service mapping used by the app (but note caveat below).
- `data/medecins.json` — doctors data and roles (admin/medecin).
- `templates/` — UI and `pdf_template.html` used for PDF generation.

## Important patterns & gotchas (do not overlook)
- Model integration: the app builds a DataFrame with columns such as `"Fever"`, `"Cough"`, `"Difficulty Breathing"`, `"Blood Pressure"` and then reorders columns using `features = features[model.feature_names_]`. Always use `model.feature_names_` to build/predict — otherwise predictions will be wrong.
- Outcome placeholder: the code adds `'Outcome Variable'` to the features DataFrame (value ignored by model) — keep this column if present in `model.feature_names_`.
- Overridden config/data: `app.py` loads `models/disease_mapping.json` early, but later in the file a hardcoded `disease_mapping` dict appears and will override the loaded mapping. Prefer the JSON file for larger mappings; check which mapping is actually used at runtime.
- Doctors source-of-truth: the app now initializes the in-memory `doctors` dict from `data/medecins.json` at startup (falls back to a small hardcoded set if the file is missing). Passwords in the JSON may be plaintext or already hashed — startup code will hash plaintext values. When modifying admin flows, update `data/medecins.json` or the loading logic in `app.py`.
-- PDF generation: `pdfkit` is used and the `wkhtmltopdf` binary path is now configurable via the `WKHTMLTOPDF_CMD` environment variable. If unset, the app falls back to the Windows default path in `app.py`.

## Dev / run / debug commands (Windows PowerShell)
1. Create & activate venv:
```
python -m venv venv
; .\venv\Scripts\Activate.ps1
```
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Ensure `wkhtmltopdf` is installed and update `pdfkit_config` path in `app.py` if necessary.
4. Run the app (development):
```
python app.py
```
5. Access app at `http://127.0.0.1:5000`.

## How predictions flow (quick example)
1. Browser POSTs form to `/result`.
2. `app.py` creates a pandas DataFrame with symptom columns, reorders using `model.feature_names_`, then calls `model.predict()` and `model.predict_proba()`.
3. The numeric class (stringified) is looked up in `disease_mapping` to produce a human-readable disease and recommended exams/service.

## Admin & auth specifics
- Login uses the in-memory `doctors` dict for password hashes (created with Werkzeug). Example user keys: `dr.smith`, `dr.martin`.
- Admin checks look for `'is_admin'` in the `doctors` dict and `role: admin` in `data/medecins.json` (see `admin_required`). When modifying admin flows, update both places or centralize to avoid inconsistencies.

## Editing guidance for common tasks
- Add/update model: save the CatBoost pickle to `models/CatBoost_best_model.pkl`. Verify `model.feature_names_` ordering and update forms to submit fields with matching names.
- Update disease mapping: edit `models/disease_mapping.json`. Verify `app.py` uses the loaded mapping (remove the hardcoded override if consolidating).
-- Change PDF behavior: update `pdfkit_config` (the app reads `WKHTMLTOPDF_CMD`) and `pdfkit.from_string()` options in `app.py` and `templates/pdf_template.html`.

## Logging & debugging tips
- The app prints debug messages and stack traces to console (see `print(...)` and `traceback.print_exc()` in `app.py`). Run `app.py` in `debug=True` (already set) to get automatic reloads.
- Common runtime errors:
  - Missing model file -> `Model file not found` or `model is None`. Ensure the pickle exists and is compatible with the code (CatBoost version).
  - Column mismatch when creating features -> KeyError on `features = features[model.feature_names_]`. Confirm the HTML form names and the DataFrame columns match exactly (including spaces).

## Where to look for follow-up changes
- UI templates: `templates/` (login, index, result, pdf_template).
- Static CSS: `static/style.css` (branding CHU colors referenced in `README.md`).
- Data & mappings: `data/medecins.json`, `models/disease_mapping.json`.

## When to ask the repo owner
- Clarify whether `data/medecins.json` or the in-memory `doctors` dict is the source of truth for production.
- Confirm expected location for `wkhtmltopdf` for CI / production (or container image) to avoid hardcoded Windows path.

---
I updated the repository to: 1) stop overriding `disease_mapping` (the app uses `models/disease_mapping.json`), 2) initialize `doctors` from `data/medecins.json` (with a small fallback), and 3) make the `wkhtmltopdf` path configurable via `WKHTMLTOPDF_CMD`.

If you'd prefer a different approach (for example: migrating `medecins.json` to a hashed-only password format, or centralizing the doctors file to a DB), tell me which next change to make.
