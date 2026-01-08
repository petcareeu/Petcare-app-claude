#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Petcare - Piattaforma Servizi Pet Care
Versione ottimizzata per Railway deployment
"""
import os
import sys
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Inizializzazione Flask
app = Flask(__name__)
CORS(app)

# Configurazione Secret Key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'petcare-secret-key-change-in-production')

# Configurazione Database
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Railway usa postgres:// ma SQLAlchemy richiede postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    logger.info("Connessione a Railway PostgreSQL")
else:
    # Fallback a SQLite per sviluppo locale
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///petcare.db'
    logger.info("Uso SQLite locale")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_timeout': 20,
    'max_overflow': 0,
    'pool_size': 5
}

# Inizializzazione Database
db = SQLAlchemy(app)

# ========== MODELLI DATABASE ==========

class User(db.Model):
    """Modello utente - sia clienti che professionisti"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    user_type = db.Column(db.String(20), nullable=False, default='client')
    
    # Campi per professionisti
    profession = db.Column(db.String(100))
    city = db.Column(db.String(100))
    region = db.Column(db.String(100))
    experience_years = db.Column(db.Integer, default=0)
    services_offered = db.Column(db.Text)
    hourly_rate = db.Column(db.Float, default=0.0)
    rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    bio = db.Column(db.Text)
    
    # Stato account
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    """Modello prenotazioni"""
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_type = db.Column(db.String(100), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text)
    total_cost = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ========== INIZIALIZZAZIONE DATABASE ==========

db_initialized = False

def init_database():
    """Inizializzazione lazy del database con dati di esempio"""
    global db_initialized
    if db_initialized:
        return True
    
    try:
        logger.info("Inizializzazione database...")
        with app.app_context():
            db.create_all()
            
            # Aggiungi dati di esempio solo se il DB è vuoto
            if User.query.count() == 0:
                logger.info("Creazione professionisti di esempio...")
                professionals = [
                    User(
                        name="Dr. Marco Rossi",
                        email="marco.rossi@petcare.it",
                        phone="+39 333 1234567",
                        user_type="professional",
                        profession="Veterinario",
                        city="Milano",
                        region="Lombardia",
                        experience_years=8,
                        services_offered="Visite generali, Chirurgia, Vaccinazioni",
                        hourly_rate=80.0,
                        rating=4.8,
                        total_reviews=156,
                        bio="Veterinario specializzato in chirurgia con 8 anni di esperienza",
                        is_verified=True
                    ),
                    User(
                        name="Laura Bianchi",
                        email="laura.bianchi@petcare.it",
                        phone="+39 347 9876543",
                        user_type="professional",
                        profession="Toelettatore",
                        city="Roma",
                        region="Lazio",
                        experience_years=5,
                        services_offered="Toelettatura completa, Bagno, Taglio unghie",
                        hourly_rate=45.0,
                        rating=4.9,
                        total_reviews=89,
                        bio="Toelettatore certificato specializzato in razze di piccola taglia",
                        is_verified=True
                    ),
                    User(
                        name="Giuseppe Verde",
                        email="giuseppe.verde@petcare.it",
                        phone="+39 320 5551234",
                        user_type="professional",
                        profession="Dog Sitter",
                        city="Napoli",
                        region="Campania",
                        experience_years=3,
                        services_offered="Passeggiate, Pet sitting, Addestramento base",
                        hourly_rate=25.0,
                        rating=4.7,
                        total_reviews=67,
                        bio="Dog sitter affidabile con passione per gli animali",
                        is_verified=True
                    ),
                    User(
                        name="Sofia Russo",
                        email="sofia.russo@petcare.it",
                        phone="+39 348 7778888",
                        user_type="professional",
                        profession="Addestratore Cinofilo",
                        city="Torino",
                        region="Piemonte",
                        experience_years=6,
                        services_offered="Addestramento avanzato, Educazione cuccioli",
                        hourly_rate=60.0,
                        rating=4.9,
                        total_reviews=123,
                        bio="Addestratore cinofilo certificato ENCI",
                        is_verified=True
                    )
                ]
                
                for prof in professionals:
                    db.session.add(prof)
                
                db.session.commit()
                logger.info(f"Creati {len(professionals)} professionisti di esempio")
            
            db_initialized = True
            logger.info("Database inizializzato con successo")
            return True
            
    except Exception as e:
        logger.error(f"Errore inizializzazione database: {e}")
        db.session.rollback()
        return False

# ========== ROUTES PUBBLICHE ==========

@app.route('/')
def home():
    """Homepage"""
    init_database()
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check per Railway"""
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        db_status = 'disconnected'
    
    return jsonify({
        'status': 'healthy',
        'database': db_status,
        'version': '3.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })

# ========== API ENDPOINTS ==========

@app.route('/api/professionals')
def get_professionals():
    """Ottieni lista professionisti"""
    try:
        init_database()
        
        # Filtri opzionali
        profession = request.args.get('profession')
        city = request.args.get('city')
        
        query = User.query.filter_by(user_type='professional', is_active=True)
        
        if profession:
            query = query.filter_by(profession=profession)
        if city:
            query = query.filter_by(city=city)
        
        professionals = query.order_by(User.rating.desc()).all()
        
        return jsonify([{
            'id': p.id,
            'name': p.name,
            'profession': p.profession or 'Professionista',
            'city': p.city or 'N/A',
            'region': p.region or 'N/A',
            'rating': p.rating,
            'total_reviews': p.total_reviews,
            'hourly_rate': p.hourly_rate,
            'services_offered': p.services_offered or 'Servizi vari',
            'bio': p.bio or 'Professionista qualificato',
            'is_verified': p.is_verified,
            'experience_years': p.experience_years
        } for p in professionals])
        
    except Exception as e:
        logger.error(f"Errore get_professionals: {e}")
        return jsonify({'error': 'Errore nel recupero dei professionisti'}), 500

@app.route('/api/professionals/<int:prof_id>')
def get_professional(prof_id):
    """Ottieni dettagli singolo professionista"""
    try:
        professional = User.query.filter_by(
            id=prof_id,
            user_type='professional',
            is_active=True
        ).first()
        
        if not professional:
            return jsonify({'error': 'Professionista non trovato'}), 404
        
        return jsonify({
            'id': professional.id,
            'name': professional.name,
            'profession': professional.profession,
            'city': professional.city,
            'region': professional.region,
            'rating': professional.rating,
            'total_reviews': professional.total_reviews,
            'hourly_rate': professional.hourly_rate,
            'services_offered': professional.services_offered,
            'bio': professional.bio,
            'is_verified': professional.is_verified,
            'experience_years': professional.experience_years,
            'phone': professional.phone
        })
        
    except Exception as e:
        logger.error(f"Errore get_professional: {e}")
        return jsonify({'error': 'Errore nel recupero del professionista'}), 500

@app.route('/api/register', methods=['POST'])
def register():
    """Registrazione nuovo utente"""
    try:
        init_database()
        data = request.get_json()
        
        # Validazione dati
        if not data or not data.get('name') or not data.get('email'):
            return jsonify({'error': 'Nome e email sono obbligatori'}), 400
        
        # Controlla se email già esiste
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email già registrata'}), 400
        
        # Crea nuovo utente
        new_user = User(
            name=data['name'],
            email=data['email'],
            phone=data.get('phone', ''),
            user_type=data.get('user_type', 'client'),
            profession=data.get('profession', ''),
            city=data.get('city', ''),
            region=data.get('region', '')
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"Nuovo utente registrato: {new_user.email}")
        return jsonify({
            'message': 'Registrazione completata con successo',
            'user_id': new_user.id
        }), 201
        
    except Exception as e:
        logger.error(f"Errore registrazione: {e}")
        db.session.rollback()
        return jsonify({'error': 'Errore durante la registrazione'}), 500

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Crea nuova prenotazione"""
    try:
        init_database()
        data = request.get_json()
        
        # Validazione
        required_fields = ['client_id', 'professional_id', 'service_type', 'booking_date']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Campi obbligatori mancanti'}), 400
        
        # Crea prenotazione
        new_booking = Booking(
            client_id=data['client_id'],
            professional_id=data['professional_id'],
            service_type=data['service_type'],
            booking_date=datetime.fromisoformat(data['booking_date']),
            notes=data.get('notes', ''),
            total_cost=data.get('total_cost', 0.0)
        )
        
        db.session.add(new_booking)
        db.session.commit()
        
        logger.info(f"Nuova prenotazione creata: {new_booking.id}")
        return jsonify({
            'message': 'Prenotazione creata con successo',
            'booking_id': new_booking.id
        }), 201
        
    except Exception as e:
        logger.error(f"Errore creazione prenotazione: {e}")
        db.session.rollback()
        return jsonify({'error': 'Errore durante la creazione della prenotazione'}), 500

# ========== ADMIN ROUTES ==========

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Login amministratore"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin_user = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_pass = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        if username == admin_user and password == admin_pass:
            session['admin_logged_in'] = True
            logger.info(f"Admin login riuscito: {username}")
            return redirect(url_for('admin_dashboard'))
        
        logger.warning(f"Tentativo login admin fallito: {username}")
        return render_template('admin_login.html', error='Credenziali non valide')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Dashboard amministratore"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    init_database()
    return render_template('admin_dashboard.html')

@app.route('/admin/logout')
def admin_logout():
    """Logout amministratore"""
    session.clear()
    logger.info("Admin logout")
    return redirect(url_for('admin_login'))

@app.route('/api/admin/stats')
def admin_stats():
    """Statistiche amministratore"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Non autorizzato'}), 401
    
    try:
        init_database()
        
        stats = {
            'total_users': User.query.count(),
            'total_professionals': User.query.filter_by(user_type='professional').count(),
            'total_clients': User.query.filter_by(user_type='client').count(),
            'verified_professionals': User.query.filter_by(
                user_type='professional',
                is_verified=True
            ).count(),
            'total_bookings': Booking.query.count(),
            'pending_bookings': Booking.query.filter_by(status='pending').count()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Errore statistiche admin: {e}")
        return jsonify({'error': 'Errore nel recupero delle statistiche'}), 500

# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(e):
    """Gestione 404"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint non trovato'}), 404
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(e):
    """Gestione 500"""
    logger.error(f"Errore interno: {e}")
    return jsonify({'error': 'Errore interno del server'}), 500

# ========== STARTUP ==========

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Avvio Petcare sulla porta {port}")
    logger.info(f"Debug mode: {debug_mode}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
