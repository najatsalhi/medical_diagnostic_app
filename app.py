from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import pdfkit
import os
import json
import pickle
import pandas as pd
import numpy as np
import uuid
import re

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_ici'

# Configure pdfkit
wkhtml_cmd = os.environ.get('WKHTMLTOPDF_CMD', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
pdfkit_config = pdfkit.configuration(wkhtmltopdf=wkhtml_cmd)

# Load the CatBoost model
model_path = 'models/CatBoost_best_model.pkl'
if os.path.exists(model_path):
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        print("CatBoost model loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        model = None
else:
    print("Model file not found")
    model = None

# Print feature names if model is loaded
if model is not None:
    feature_names = model.feature_names_
    print(f"Feature names (CatBoost): {feature_names}")
else:
    print("No feature names available - model not loaded")

# Load disease mapping
with open('models/disease_mapping.json', 'r') as f:
    disease_mapping = json.load(f)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Vous devez être connecté pour accéder à cette page.', 'error')
            return redirect(url_for('login'))
        
        username = session.get('username')
        print(f"Checking admin rights for: {username}")  # Debug print
        
        data_path = os.path.join('data', 'medecins.json')
        try:
            # Prefer the in-memory `doctors` dict which is initialized from `data/medecins.json` at startup.
            if username in doctors and doctors[username].get('is_admin', False):
                print(f"Admin access granted for (in-memory): {username}")
                return f(*args, **kwargs)

            # Fallback: check raw data file for role information
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as file:
                    medecins = json.load(file)
                    if username in medecins and medecins[username].get('role') == 'admin':
                        print(f"Admin access granted for (file): {username}")  # Debug print
                        return f(*args, **kwargs)

            print(f"Admin access denied for: {username}")  # Debug print
            flash('Vous n\'avez pas les droits administrateur nécessaires.', 'error')
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Error checking admin rights: {str(e)}")  # Debug print
            flash('Erreur lors de la vérification des droits.', 'error')
            return redirect(url_for('index'))
    
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('index.html',
                         nom_medecin=session.get('nom_medecin'),
                         specialite=session.get('specialite'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in doctors and check_password_hash(doctors[username]['password'], password):
            if not doctors[username].get('is_active', True):
                flash('Compte désactivé. Contactez l\'administrateur.', 'error')
                return redirect(url_for('login'))
                
            session['username'] = username
            session['nom_medecin'] = doctors[username]['nom']
            session['specialite'] = doctors[username]['specialite']
            session['is_admin'] = doctors[username].get('is_admin', False)
            flash('Connexion réussie', 'success')
            return redirect(url_for('index'))
            
        flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté', 'success')
    return redirect(url_for('login'))

# Admin dashboard route
@app.route('/admin')
@login_required
def admin_dashboard():
    try:
        username = session.get('username')
        if not username:
            flash('Veuillez vous connecter', 'error')
            return redirect(url_for('login'))

        if username not in doctors or not doctors[username].get('is_admin', False):
            flash('Accès non autorisé', 'error')
            return redirect(url_for('index'))

        print(f"Admin access granted for: {username}")
        print(f"Admin Dashboard - Loaded doctors: {doctors.keys()}")

        # Load recent activity from data/recent_activity.json when available, otherwise provide sensible defaults
        recent_activity_path = os.path.join('data', 'recent_activity.json')
        recent_activity = []
        try:
            if os.path.exists(recent_activity_path):
                with open(recent_activity_path, 'r', encoding='utf-8') as rf:
                    recent_activity = json.load(rf)
            else:
                # sample fallback entries (developer-friendly)
                recent_activity = [
                    {'icon': '🔒', 'title': "Dr. Martin s'est connecté", 'time': 'Il y a 2 heures'},
                    {'icon': '📝', 'title': 'Nouveau diagnostic: Patient #A54781', 'time': "Aujourd'hui, 10:45"},
                    {'icon': '👨‍⚕️', 'title': 'Nouveau médecin: Dr. Sarah Benani', 'time': 'Hier, 14:30'}
                ]
        except Exception as e:
            print(f"Warning: could not load recent activity: {e}")

        # Load patients for admin view (recent predictions)
        patients = []
        try:
            patients_path = os.path.join('data', 'patients.json')
            if os.path.exists(patients_path):
                with open(patients_path, 'r', encoding='utf-8') as pf:
                    patients = json.load(pf)
        except Exception as e:
            print(f"Warning: could not load patients for admin dashboard: {e}")

        return render_template('admin_dashboard.html',
                             doctors=doctors,
                             recent_activity=recent_activity,
                             patients=patients,
                             current_user=username,
                             nom_medecin=session.get('nom_medecin'),
                             specialite=session.get('specialite'))

    except Exception as e:
        print(f"Error in admin_dashboard: {str(e)}")
        # Show detailed error only when app is running in debug mode
        detail = f": {e}" if app.debug else ''
        flash(f'Erreur lors du chargement du tableau de bord{detail}', 'error')
        return redirect(url_for('index'))


@app.route('/api/admin/recent-activity')
@login_required
def api_admin_recent_activity():
    """Return recent activity as JSON for the admin dashboard.
    Requires login; returns the same payload used by the template.
    """
    # Only allow admins to fetch detailed activity
    if not session.get('is_admin'):
        return jsonify({'error': 'Accès non autorisé'}), 403

    recent_activity_path = os.path.join('data', 'recent_activity.json')
    recent_activity = []
    try:
        if os.path.exists(recent_activity_path):
            with open(recent_activity_path, 'r', encoding='utf-8') as rf:
                recent_activity = json.load(rf)
        else:
            recent_activity = [
                {'icon': '🔒', 'title': "Dr. Martin s'est connecté", 'time': 'Il y a 2 heures'},
                {'icon': '📝', 'title': 'Nouveau diagnostic: Patient #A54781', 'time': "Aujourd'hui, 10:45"},
                {'icon': '👨‍⚕️', 'title': 'Nouveau médecin: Dr. Sarah Benani', 'time': 'Hier, 14:30'}
            ]
    except Exception as e:
        print(f"Warning: could not load recent activity for API: {e}")
        recent_activity = []

    return jsonify({'recent_activity': recent_activity})

def generate_pdf_report(prediction_result):
    try:
        html = render_template('pdf_template.html',
                             prediction_result=prediction_result,
                             medecin_info={
                                 'nom': session.get('nom_medecin'),
                                 'specialite': session.get('specialite')
                             },
                             current_date=datetime.now().strftime('%d/%m/%Y %H:%M'))
        
        pdf = pdfkit.from_string(html, False, configuration=pdfkit_config)
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=diagnostic_{prediction_result["patient_info"]["cne"]}.pdf'
        
        return response
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        flash('Erreur lors de la génération du PDF.', 'error')
        return redirect(url_for('index'))

# Load doctors from data/medecins.json and normalize into the `doctors` dict used by the app
doctors = {}
data_medecins_path = os.path.join('data', 'medecins.json')
def is_hashed_password(pwd: str) -> bool:
    """Return True if `pwd` looks like a Werkzeug/secure hash we accept."""
    if not isinstance(pwd, str):
        return False
    # common Werkzeug prefixes or scrypt used by current environment
    return pwd.startswith('pbkdf2:') or pwd.startswith('scrypt:') or pwd.startswith('argon2:')
if os.path.exists(data_medecins_path):
    try:
        with open(data_medecins_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        for username, info in raw.items():
            pwd = info.get('password', '')
            if is_hashed_password(pwd):
                stored_pwd = pwd
            else:
                # Found plaintext or unsupported hash: warn and hash in-memory
                print(f"Warning: password for {username} does not appear hashed. Hashing in-memory (not persisted).")
                stored_pwd = generate_password_hash(pwd or 'password123')

            doctors[username] = {
                'password': stored_pwd,
                'nom': info.get('nom_complet') or info.get('nom') or username,
                'specialite': info.get('specialite', ''),
                'email': info.get('email', ''),
                'is_active': info.get('is_active', True),
                'is_admin': info.get('role', '') == 'admin'
            }
        print(f"Loaded {len(doctors)} doctors from {data_medecins_path}")
    except Exception as e:
        print(f"Error loading doctors from {data_medecins_path}: {e}")

# Fallback hardcoded doctors (only used if file missing or empty)
if not doctors:
    doctors = {
        'dr.smith': {
            'password': generate_password_hash('password123'),
            'nom': 'Dr. Smith',
            'specialite': 'Cardiologue',
            'is_active': True,
            'is_admin': True
        },
        'dr.martin': {
            'password': generate_password_hash('password123'),
            'nom': 'Dr. Martin',
            'specialite': 'Pneumologue',
            'is_active': True,
            'is_admin': False
        }
    }

# Password reset tokens (file-backed): token -> {'username': str, 'expires': datetime}
password_reset_tokens = {}
password_tokens_path = os.path.join('data', 'password_reset_tokens.json')


def _cleanup_expired_tokens_dict(tokens: dict) -> dict:
    now = datetime.now()
    return {t: v for t, v in tokens.items() if v.get('expires') and v['expires'] > now}


def load_password_tokens():
    global password_reset_tokens
    if not os.path.exists(password_tokens_path):
        password_reset_tokens = {}
        return
    try:
        with open(password_tokens_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        tokens = {}
        for token, info in raw.items():
            expires_raw = info.get('expires')
            try:
                expires_dt = datetime.fromisoformat(expires_raw) if expires_raw else None
            except Exception:
                expires_dt = None
            tokens[token] = {'username': info.get('username'), 'expires': expires_dt}

        # Remove expired
        password_reset_tokens = _cleanup_expired_tokens_dict(tokens)
    except Exception as e:
        print(f"Warning: could not load password tokens: {e}")
        password_reset_tokens = {}


def save_password_tokens():
    try:
        serializable = {}
        for token, info in password_reset_tokens.items():
            expires = info.get('expires')
            serializable[token] = {
                'username': info.get('username'),
                'expires': expires.isoformat() if expires else None
            }
        # ensure data dir exists
        os.makedirs(os.path.dirname(password_tokens_path), exist_ok=True)
        with open(password_tokens_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Warning: could not save password tokens: {e}")


# Load tokens at startup
load_password_tokens()

# NOTE: `models/disease_mapping.json` is the authoritative mapping of class -> {name, examens, service}
# The file is loaded near the top of this module into `disease_mapping`.
def get_recommended_service(disease_name):
    for entry in disease_mapping.values():
        if entry.get('name') == disease_name:
            return entry.get('service', 'Service de Médecine Générale')
    return 'Service de Médecine Générale'

def get_recommended_exams(disease_name):
    for entry in disease_mapping.values():
        if entry.get('name') == disease_name:
            return entry.get('examens', ['Consultation médicale approfondie'])
    return ['Consultation médicale approfondie']


# Build a mapping from alphanumeric id -> actual username key so users can use `id`
ids_map = {}
for username_key, info in doctors.items():
    # prefer explicit 'id' from source file if present
    explicit_id = None
    try:
        with open(data_medecins_path, 'r', encoding='utf-8') as f:
            raw_file = json.load(f)
            explicit_id = raw_file.get(username_key, {}).get('id')
    except Exception:
        explicit_id = None

    if explicit_id:
        uid = explicit_id
    else:
        # derive id by removing non-alphanumeric chars
        uid = re.sub(r'[^A-Za-z0-9]', '', username_key)

    doctors[username_key]['id'] = uid
    ids_map[uid] = username_key

@app.route('/result', methods=['POST'])
@login_required
def result():
    if request.method == 'POST':
        try:
            # Create features DataFrame
            features = pd.DataFrame({
                'Fever': [float(request.form.get('fever', 0))],
                'Cough': [float(request.form.get('cough', 0))],
                'Fatigue': [float(request.form.get('fatigue', 0))],
                'Difficulty Breathing': [float(request.form.get('difficulty_breathing', 0))],
                'Age': [float(request.form.get('age', 0))],
                'Gender': [float(request.form.get('gender', 0))],
                'Blood Pressure': [float(request.form.get('blood_pressure', 0))],
                'Cholesterol Level': [float(request.form.get('cholesterol_level', 0))],
                'Outcome Variable': [0.0]  # Required by model, will be ignored for prediction
            })

            # Ensure column order matches model's expectations
            features = features[model.feature_names_]
            
            # Make prediction
            raw_prediction = model.predict(features)
            probabilities = model.predict_proba(features)
            
            # Convert prediction to string for dictionary lookup
            disease_class = str(int(raw_prediction.item()))
            confidence = float(np.max(probabilities[0])) * 100

            # Map class -> disease entry from models/disease_mapping.json
            d_entry = disease_mapping.get(disease_class)
            if d_entry:
                disease_name = d_entry.get('name', 'Maladie inconnue')
                service = d_entry.get('service', 'Service de Médecine Générale')
                exams = d_entry.get('examens', ['Consultation médicale approfondie'])
            else:
                disease_name = 'Maladie inconnue'
                service = 'Service de Médecine Générale'
                exams = ['Consultation médicale approfondie']

            # Build result dictionary
            result_data = {
                'patient': {
                    'nom': request.form.get('LastName', ''),
                    'prenom': request.form.get('FirstName', ''),
                    'cne': request.form.get('CNE', ''),
                    'age': request.form.get('age', ''),
                    'genre': 'Femme' if int(request.form.get('gender', 0)) == 1 else 'Homme'
                },
                'symptoms': {
                    'fievre': 'Oui' if int(request.form.get('fever', 0)) == 1 else 'Non',
                    'toux': 'Oui' if int(request.form.get('cough', 0)) == 1 else 'Non',
                    'fatigue': 'Oui' if int(request.form.get('fatigue', 0)) == 1 else 'Non',
                    'respiration': 'Oui' if int(request.form.get('difficulty_breathing', 0)) == 1 else 'Non'
                },
                'diagnostic': {
                    'maladie': disease_name,
                    'confiance': f"{confidence:.1f}%",
                    'service': service,
                    'examens': exams
                },
                'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'medecin': {
                    'nom': session.get('nom_medecin', ''),
                    'specialite': session.get('specialite', '')
                }
            }

            # Persist patient prediction to data/patients.json so admin can review per-doctor lists
            try:
                patients_path = os.path.join('data', 'patients.json')
                os.makedirs(os.path.dirname(patients_path), exist_ok=True)
                patients = []
                if os.path.exists(patients_path):
                    try:
                        with open(patients_path, 'r', encoding='utf-8') as pf:
                            patients = json.load(pf)
                            if not isinstance(patients, list):
                                patients = []
                    except Exception:
                        patients = []

                patient_entry = {
                    'nom': result_data['patient'].get('nom', ''),
                    'prenom': result_data['patient'].get('prenom', ''),
                    'cin': result_data['patient'].get('cne', ''),
                    'age': result_data['patient'].get('age', ''),
                    'sex': result_data['patient'].get('genre', ''),
                    'disease': result_data['diagnostic'].get('maladie', ''),
                    'doctor': result_data['medecin'].get('nom', ''),
                    'service': result_data['diagnostic'].get('service', ''),
                    'date': result_data.get('date', datetime.now().strftime('%d/%m/%Y %H:%M'))
                }

                patients.insert(0, patient_entry)
                # keep most recent 1000 entries to avoid unbounded growth
                patients = patients[:1000]
                with open(patients_path, 'w', encoding='utf-8') as pf:
                    json.dump(patients, pf, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"Warning: could not persist patient entry: {e}")

            print("Debug - Result Data:", result_data)  # Debug print
            return render_template('result.html', result=result_data)

        except Exception as e:
            print(f"Error during prediction: {str(e)}")
            import traceback
            traceback.print_exc()  # Print full stack trace
            flash("Une erreur s'est produite lors du diagnostic", 'error')
            return redirect(url_for('index'))

    return redirect(url_for('index'))

@app.route('/admin/toggle-status', methods=['POST'])
@login_required
def toggle_doctor_status():
    if not session.get('is_admin'):
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    username = request.form.get('username')
    if username in doctors:
        doctors[username]['is_active'] = not doctors[username].get('is_active', True)
        flash(f'Statut du médecin {username} mis à jour', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-doctor', methods=['POST'])
@login_required
def add_doctor():
    if not session.get('is_admin'):
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    # Read submitted fields. We auto-generate both the JSON key (username_key) and the alphanumeric `id`.
    nom_complet = request.form.get('nom_complet')
    specialite = request.form.get('specialite')
    password = request.form.get('password')
    email = request.form.get('email', '').strip()

    # Generate signature and numero_ordre automatically
    # Signature: standard block with doctor's name and specialty
    generated_signature = f"Dr. {nom_complet}\n{specialite}\nCHU Mohammed VI Oujda"

    # Generate a unique numeric 'numero_ordre'. Prefer incrementing existing numeric values.
    generated_numero = ''
    try:
        existing_nums = [int(v.get('numero_ordre')) for v in raw.values() if v.get('numero_ordre') and str(v.get('numero_ordre')).isdigit()]
        if existing_nums:
            generated_numero = str(max(existing_nums) + 1)
        else:
            # start from 100000 + number of entries to reduce collision chance
            generated_numero = str(100000 + len(raw) + 1)
    except Exception:
        generated_numero = str(100000 + len(raw) + 1)

    if not all([nom_complet, specialite, password]):
        flash('Les champs obligatoires (nom complet, spécialité, mot de passe) sont requis', 'error')
        return redirect(url_for('admin_dashboard'))

    # Load persisted file to perform uniqueness checks
    raw = {}
    try:
        if os.path.exists(data_medecins_path):
            with open(data_medecins_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
    except Exception as e:
        print(f"Warning: could not read {data_medecins_path} for uniqueness checks: {e}")

    # Create a username key for internal storage: prefer 'dr.' + lowercase name with dots replacing spaces
    base_key = 'dr.' + re.sub(r'[^A-Za-z0-9]+', '.', nom_complet.strip().lower()).strip('.')
    username_key = base_key
    suffix = 1
    while username_key in doctors or username_key in raw:
        suffix += 1
        username_key = f"{base_key}{suffix}"

    # Generate alphanumeric id (used for external id mapping). Start from username_key but remove non-alnum
    generated_id = re.sub(r'[^A-Za-z0-9]', '', username_key).lower() or uuid.uuid4().hex[:8]
    # Ensure id uniqueness in persisted records
    id_suffix = 1
    existing_ids = {v.get('id') for v in raw.values() if v.get('id')}
    while generated_id in existing_ids:
        id_suffix += 1
        generated_id = f"{generated_id}{id_suffix}"

    # Hash password and prepare in-memory entry
    hashed = generate_password_hash(password)
    doctors[username_key] = {
        'password': hashed,
        'nom': nom_complet,
        'specialite': specialite,
        'email': email,
        'is_active': True,
        'is_admin': False,
        'id': generated_id,
        'numero_ordre': generated_numero,
        'signature': generated_signature
    }

    # Persist to data/medecins.json (preserve other entries)
    try:
        raw = {}
        if os.path.exists(data_medecins_path):
            with open(data_medecins_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)

        raw[username_key] = {
            'id': generated_id,
            'password': hashed,
            'nom_complet': nom_complet,
            'specialite': specialite,
            'numero_ordre': generated_numero,
            'email': email,
            'signature': generated_signature,
            'role': 'medecin'
        }

        # Backup existing file before overwriting
        try:
            if os.path.exists(data_medecins_path):
                backup_path = data_medecins_path + ".bak"
                with open(data_medecins_path, 'r', encoding='utf-8') as fsrc, open(backup_path, 'w', encoding='utf-8') as fdst:
                    fdst.write(fsrc.read())
        except Exception:
            pass

        with open(data_medecins_path, 'w', encoding='utf-8') as f:
            json.dump(raw, f, ensure_ascii=False, indent=4)

        # Update ids_map so forget-password and other flows can use the new id immediately
        ids_map[generated_id] = username_key

        flash(f'Médecin ajouté avec succès (identifiant généré: {generated_id})', 'success')
    except Exception as e:
        print(f"Error persisting new doctor: {e}")
        flash('Médecin ajouté en mémoire mais la sauvegarde a échoué', 'warning')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset-password', methods=['POST'])
@login_required
def reset_password():
    if not session.get('is_admin'):
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    username = request.form.get('username')
    if username in doctors:
        new_password = 'password123'  # Default reset password
        doctors[username]['password'] = generate_password_hash(new_password)
        flash(f'Mot de passe réinitialisé pour {username}', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/download-pdf', methods=['POST'])
@login_required
def download_pdf():
    try:
        result_data = json.loads(request.form.get('result_data'))
        
        html = render_template('pdf_template.html', 
                             result=result_data,
                             date=datetime.now().strftime('%d/%m/%Y %H:%M'))
        
        # Generate PDF
        pdf = pdfkit.from_string(html, False, configuration=pdfkit_config, options={
            'encoding': 'UTF-8',
            'page-size': 'A4',
            'margin-top': '1cm',
            'margin-right': '1cm',
            'margin-bottom': '1cm',
            'margin-left': '1cm'
        })
        
        # Create response
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=diagnostic_{result_data["patient"]["nom"]}_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        return response
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        flash("Erreur lors de la génération du PDF", 'error')
        return redirect(url_for('index'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        # Require BOTH username and email, and ensure they match the same account.
        username_input = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()

        if not username_input or not email:
            flash('Les deux champs sont requis : identifiant et email.', 'error')
            return render_template('forgot_password.html', current_year=datetime.now().year)

        # Verify username format (letters and numbers only)
        if not re.fullmatch(r'[A-Za-z0-9]+', username_input):
            flash("Le nom d'utilisateur doit contenir uniquement des lettres et des chiffres.", 'error')
            return render_template('forgot_password.html', current_year=datetime.now().year)

        # Verify username exists and email matches. Support alphanumeric `id` mapping.
        found_user = None
        # Direct key (unlikely because keys may contain dots)
        if username_input in doctors:
            if doctors[username_input].get('email', '').strip().lower() == email:
                found_user = username_input
        else:
            # Check ids_map (id -> real username key)
            mapped = ids_map.get(username_input)
            if mapped and doctors.get(mapped, {}).get('email', '').strip().lower() == email:
                found_user = mapped
            else:
                # fallback: check raw medecins.json for either key or id
                try:
                    with open(data_medecins_path, 'r', encoding='utf-8') as f:
                        raw = json.load(f)
                    # check if input matches a key and email
                    if username_input in raw and raw[username_input].get('email', '').strip().lower() == email:
                        found_user = username_input
                    else:
                        # check if matches an 'id' value in raw
                        for k, v in raw.items():
                            if v.get('id') == username_input and v.get('email', '').strip().lower() == email:
                                found_user = k
                                break
                except Exception:
                    pass

        if not found_user:
            flash('Identifiant et email ne correspondent pas à un compte valide.', 'error')
            return render_template('forgot_password.html', current_year=datetime.now().year)

        # Create token and continue as before
        token = uuid.uuid4().hex
        expires = datetime.now() + timedelta(minutes=15)
        password_reset_tokens[token] = {'username': found_user, 'expires': expires}
        save_password_tokens()
        # Debug-mode immediate redirect for development convenience
        if app.debug:
            return redirect(url_for('reset_password_token', token=token))
        reset_link = url_for('reset_password_token', token=token, _external=True)
        flash('Un lien de réinitialisation a été envoyé (en dev il est affiché ci-dessous).', 'success')
        return render_template('forgot_password.html', reset_link=reset_link, current_year=datetime.now().year)

        if not found_user:
            # Try raw data file as fallback
            try:
                with open(data_medecins_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                for username, info in raw.items():
                    if info.get('email', '').strip().lower() == email:
                        found_user = username
                        break
            except Exception:
                pass

        if not found_user:
            flash('Aucun compte trouvé pour cette adresse email.', 'error')
            return render_template('forgot_password.html', current_year=datetime.now().year)

        # Generate token and store with expiry (15 minutes)
        token = uuid.uuid4().hex
        expires = datetime.now() + timedelta(minutes=15)
        password_reset_tokens[token] = {'username': found_user, 'expires': expires}
        # save to disk so token survives restarts
        save_password_tokens()

        # Create reset link (for dev we render the link so developer can click it)
        reset_link = url_for('reset_password_token', token=token, _external=True)
        flash('Un lien de réinitialisation a été généré (en environnement de développement il est affiché ci-dessous).', 'success')
        return render_template('forgot_password.html', reset_link=reset_link, current_year=datetime.now().year)

    return render_template('forgot_password.html', current_year=datetime.now().year)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_token(token):
    info = password_reset_tokens.get(token)
    if not info:
        flash('Lien invalide ou expiré.', 'error')
        return redirect(url_for('forgot_password'))

    if not info.get('expires') or datetime.now() > info['expires']:
        password_reset_tokens.pop(token, None)
        save_password_tokens()
        flash('Le lien de réinitialisation a expiré.', 'error')
        return redirect(url_for('forgot_password'))

    username = info['username']
    if request.method == 'POST':
        pwd = request.form.get('password')
        pwd2 = request.form.get('confirm_password')
        if not pwd or pwd != pwd2:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return render_template('reset_password.html')

        # Update in-memory
        if username in doctors:
            doctors[username]['password'] = generate_password_hash(pwd)
        # Persist to data file if present
        try:
            if os.path.exists(data_medecins_path):
                with open(data_medecins_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                if username in raw:
                    raw[username]['password'] = doctors.get(username, {}).get('password', generate_password_hash(pwd))
                    with open(data_medecins_path, 'w', encoding='utf-8') as f:
                        json.dump(raw, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Warning: could not persist password to {data_medecins_path}: {e}")

        # Consume token
        password_reset_tokens.pop(token, None)
        save_password_tokens()
        flash('Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

if __name__ == '__main__':
    app.run(debug=True)