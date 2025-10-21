from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import pdfkit
import os
import json
import pickle
import pandas as pd
import numpy as np

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_ici'

# Configure pdfkit
pdfkit_config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

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
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as file:
                    medecins = json.load(file)
                    if username in medecins and medecins[username].get('role') == 'admin':
                        print(f"Admin access granted for: {username}")  # Debug print
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

        return render_template('admin_dashboard.html',
                             doctors=doctors,
                             current_user=username,
                             nom_medecin=session.get('nom_medecin'),
                             specialite=session.get('specialite'))

    except Exception as e:
        print(f"Error in admin_dashboard: {str(e)}")
        flash('Erreur lors du chargement du tableau de bord', 'error')
        return redirect(url_for('index'))

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

# Add this at the top with other global variables
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
    },
    'dr.bernard': {
        'password': generate_password_hash('password123'),
        'nom': 'Dr. Bernard',
        'specialite': 'Médecin Généraliste',
        'is_active': True,
        'is_admin': False
    },
    'dr.moreau': {
        'password': generate_password_hash('password123'),
        'nom': 'Dr. Moreau',
        'specialite': 'Pneumologue',
        'is_active': True,
        'is_admin': False
    },
    'dr.lefevre': {
        'password': generate_password_hash('password123'),
        'nom': 'Dr. Lefevre',
        'specialite': 'Cardiologue',
        'is_active': True,
        'is_admin': False
    },
    'dr.dupont': {
        'password': generate_password_hash('password123'),
        'nom': 'Dr. Dupont',
        'specialite': 'Généraliste',
        'is_active': True,
        'is_admin': False
    }
}

# Define disease mappings as simple dictionary with string keys
disease_mapping = {
    "0": "Pneumonie",
    "1": "Bronchite",
    "2": "Grippe",
    "3": "Covid-19"
}

def get_recommended_service(disease):
    services = {
        "Pneumonie": "Service de Pneumologie",
        "Bronchite": "Service de Pneumologie",
        "Grippe": "Service de Médecine Générale",
        "Covid-19": "Service des Maladies Infectieuses"
    }
    return services.get(disease, "Service de Médecine Générale")

def get_recommended_exams(disease):
    exams = {
        "Pneumonie": ["Radiographie thoracique", "Test sanguin", "Test PCR"],
        "Bronchite": ["Auscultation", "Test sanguin", "Spirométrie"],
        "Grippe": ["Test grippal", "Examen physique"],
        "Covid-19": ["Test PCR", "Scanner thoracique"]
    }
    return exams.get(disease, ["Consultation médicale approfondie"])

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
            
            # Get disease name and recommendations
            disease = disease_mapping.get(disease_class, "Maladie inconnue")
            service = get_recommended_service(disease)
            exams = get_recommended_exams(disease)

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
                    'maladie': disease,
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
    
    username = request.form.get('username')
    nom = request.form.get('nom')
    specialite = request.form.get('specialite')
    password = request.form.get('password')
    
    if not all([username, nom, specialite, password]):
        flash('Tous les champs sont requis', 'error')
        return redirect(url_for('admin_dashboard'))
        
    if username in doctors:
        flash('Ce nom d\'utilisateur existe déjà', 'error')
    else:
        doctors[username] = {
            'password': generate_password_hash(password),
            'nom': nom,
            'specialite': specialite,
            'is_active': True,
            'is_admin': False
        }
        flash('Médecin ajouté avec succès', 'success')
    
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

if __name__ == '__main__':
    app.run(debug=True)