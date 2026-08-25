# essai4.py - Application Hospitalière Complète Version 3.0
import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# ==================== CONFIGURATION ====================
st.set_page_config(
    page_title="🏥 Gestion Hospitalière",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== DATABASE ====================
class Database:
    def init_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Création des tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                age INTEGER NOT NULL,
                sexe TEXT NOT NULL,
                telephone TEXT NOT NULL,
                email TEXT,
                date_inscription TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medecins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                specialite TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                mot_de_passe TEXT NOT NULL,
                duree_consultation INTEGER DEFAULT 15
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT UNIQUE NOT NULL,
                description TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rendez_vous (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                medecin_generaliste_id INTEGER,
                medecin_specialiste_id INTEGER,
                service_id INTEGER,
                date_rdv TEXT NOT NULL,
                heure_rdv TEXT NOT NULL,
                statut TEXT DEFAULT 'en_attente',
                priorite INTEGER DEFAULT 0,
                score_priorite INTEGER DEFAULT 0,
                symptomes TEXT,
                diagnostic TEXT,
                observation TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                annule_automatique INTEGER DEFAULT 0,
                heure_annulation TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                FOREIGN KEY (medecin_generaliste_id) REFERENCES medecins(id),
                FOREIGN KEY (medecin_specialiste_id) REFERENCES medecins(id),
                FOREIGN KEY (service_id) REFERENCES services(id)
            )
        ''')
        
        # MIGRATION : Ajouter les colonnes si elles n'existent pas
        cursor.execute("PRAGMA table_info(rendez_vous)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'annule_automatique' not in columns:
            cursor.execute("ALTER TABLE rendez_vous ADD COLUMN annule_automatique INTEGER DEFAULT 0")
            print("✅ Colonne 'annule_automatique' ajoutée")
        
        if 'heure_annulation' not in columns:
            cursor.execute("ALTER TABLE rendez_vous ADD COLUMN heure_annulation TEXT")
            print("✅ Colonne 'heure_annulation' ajoutée")
        
        # Données par défaut - Médecins
        cursor.execute("SELECT COUNT(*) FROM medecins")
        if cursor.fetchone()[0] == 0:
            medecins = [
                ("Koffi", "Jean", "Généraliste", "dr.koffi@hopital.com", "admin123", 15),
                ("Amadou", "Moussa", "Cardiologue", "dr.amadou@hopital.com", "admin123", 20),
                ("Ade", "Yvette", "Gynécologue", "dr.ade@hopital.com", "admin123", 20),
                ("Komi", "Pierre", "Pédiatre", "dr.komi@hopital.com", "admin123", 15),
                ("Admin", "System", "Administrateur", "admin@hopital.com", "admin123", 15)
            ]
            cursor.executemany('''
                INSERT INTO medecins (nom, prenom, specialite, email, mot_de_passe, duree_consultation)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', medecins)
        
        # Données par défaut - Services
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            services = [
                ("Cardiologie", "Maladies du coeur"),
                ("Pneumologie", "Maladies respiratoires"),
                ("Neurologie", "Système nerveux"),
                ("Dermatologie", "Maladies de la peau"),
                ("Ophtalmologie", "Maladies des yeux"),
                ("Gynécologie", "Santé de la femme"),
                ("Pédiatrie", "Enfants"),
                ("Orthopédie", "Système musculo-squelettique")
            ]
            cursor.executemany(
                "INSERT INTO services (nom, description) VALUES (?, ?)",
                services
            )
        
        conn.commit()
        conn.close()
    
    def get_patient_by_nom_prenom(self, nom, prenom):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE nom LIKE ? AND prenom LIKE ?", 
                      (f"%{nom}%", f"%{prenom}%"))
        patients = cursor.fetchall()
        conn.close()
        return patients
    
    def get_patient_by_id(self, patient_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        patient = cursor.fetchone()
        conn.close()
        return patient
    
    def get_medecin_by_email(self, email):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medecins WHERE email = ?", (email,))
        medecin = cursor.fetchone()
        conn.close()
        return medecin
    
    def get_medecin_by_id(self, medecin_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medecins WHERE id = ?", (medecin_id,))
        medecin = cursor.fetchone()
        conn.close()
        return medecin
    
    def get_medecins_by_specialite(self, specialite):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medecins WHERE specialite LIKE ?", (f"%{specialite}%",))
        medecins = cursor.fetchall()
        conn.close()
        return medecins
    
    def get_all_medecins(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medecins ORDER BY nom")
        medecins = cursor.fetchall()
        conn.close()
        return medecins
    
    def get_services(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM services ORDER BY nom")
        services = cursor.fetchall()
        conn.close()
        return services
    
    def ajouter_rendez_vous(self, patient_id, service_id, date_rdv, heure_rdv, 
                           symptomes=None, medecin_generaliste_id=None, 
                           medecin_specialiste_id=None, priorite=0, score_priorite=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rendez_vous 
            (patient_id, service_id, date_rdv, heure_rdv, symptomes, 
             medecin_generaliste_id, medecin_specialiste_id, priorite, score_priorite, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (patient_id, service_id, date_rdv, heure_rdv, symptomes, 
              medecin_generaliste_id, medecin_specialiste_id, priorite, score_priorite, 'en_attente'))
        rdv_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return rdv_id
    
    def get_rendez_vous_by_patient(self, patient_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, s.nom as service_nom, 
                   p.nom as patient_nom, p.prenom as patient_prenom
            FROM rendez_vous r
            LEFT JOIN services s ON r.service_id = s.id
            LEFT JOIN patients p ON r.patient_id = p.id
            WHERE r.patient_id = ?
            ORDER BY r.date_rdv, r.heure_rdv
        ''', (patient_id,))
        rdvs = cursor.fetchall()
        conn.close()
        return rdvs
    
    def get_rendez_vous_by_medecin(self, medecin_id, date=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if date:
            cursor.execute('''
                SELECT r.*, p.nom as patient_nom, p.prenom as patient_prenom,
                       s.nom as service_nom
                FROM rendez_vous r
                JOIN patients p ON r.patient_id = p.id
                LEFT JOIN services s ON r.service_id = s.id
                WHERE (r.medecin_generaliste_id = ? OR r.medecin_specialiste_id = ?)
                AND r.date_rdv = ?
                AND r.statut != 'annule'
                AND r.annule_automatique = 0
                ORDER BY r.heure_rdv
            ''', (medecin_id, medecin_id, date))
        else:
            cursor.execute('''
                SELECT r.*, p.nom as patient_nom, p.prenom as patient_prenom,
                       s.nom as service_nom
                FROM rendez_vous r
                JOIN patients p ON r.patient_id = p.id
                LEFT JOIN services s ON r.service_id = s.id
                WHERE (r.medecin_generaliste_id = ? OR r.medecin_specialiste_id = ?)
                AND r.statut != 'annule'
                AND r.annule_automatique = 0
                ORDER BY r.date_rdv, r.heure_rdv
            ''', (medecin_id, medecin_id))
        rdvs = cursor.fetchall()
        conn.close()
        return rdvs
    
    def get_rendez_vous_en_attente(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, p.nom as patient_nom, p.prenom as patient_prenom,
                   s.nom as service_nom
            FROM rendez_vous r
            JOIN patients p ON r.patient_id = p.id
            LEFT JOIN services s ON r.service_id = s.id
            WHERE r.statut = 'en_attente'
            AND r.medecin_generaliste_id IS NULL
            AND r.annule_automatique = 0
            ORDER BY r.date_rdv, r.heure_rdv
        ''')
        rdvs = cursor.fetchall()
        conn.close()
        return rdvs
    
    def get_all_rendez_vous(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, p.nom as patient_nom, p.prenom as patient_prenom,
                   s.nom as service_nom
            FROM rendez_vous r
            JOIN patients p ON r.patient_id = p.id
            LEFT JOIN services s ON r.service_id = s.id
            ORDER BY r.date_rdv, r.heure_rdv
        ''')
        rdvs = cursor.fetchall()
        conn.close()
        return rdvs
    
    def update_rendez_vous(self, rdv_id, **kwargs):
        conn = self.get_connection()
        cursor = conn.cursor()
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(rdv_id)
        query = f"UPDATE rendez_vous SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        conn.close()
    
    def verifier_et_annuler_rdv_passes(self):
        """Vérifie et annule automatiquement les rendez-vous dont l'heure est dépassée"""
        maintenant = datetime.now()
        date_actuelle = maintenant.strftime("%Y-%m-%d")
        heure_actuelle = maintenant.strftime("%H:%M")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Récupérer les rendez-vous en attente ou confirmés dont la date est passée
        cursor.execute('''
            SELECT r.*, p.nom, p.prenom, p.telephone
            FROM rendez_vous r
            JOIN patients p ON r.patient_id = p.id
            WHERE r.statut IN ('en_attente', 'confirme')
            AND r.annule_automatique = 0
            AND (
                r.date_rdv < ? 
                OR (r.date_rdv = ? AND r.heure_rdv < ?)
            )
        ''', (date_actuelle, date_actuelle, heure_actuelle))
        
        rdvs_expires = cursor.fetchall()
        messages = []
        
        for rdv in rdvs_expires:
            # Annuler le rendez-vous
            cursor.execute('''
                UPDATE rendez_vous 
                SET statut = 'annule', annule_automatique = 1, heure_annulation = ?
                WHERE id = ?
            ''', (heure_actuelle, rdv[0]))
            
            # Préparer le message pour le patient
            patient_nom = rdv[-3] if len(rdv) > 16 else "Patient"
            patient_prenom = rdv[-2] if len(rdv) > 16 else ""
            messages.append({
                'patient': f"{patient_prenom} {patient_nom}",
                'telephone': rdv[-1] if len(rdv) > 16 else "Non renseigné",
                'date': rdv[5],
                'heure': rdv[6],
                'rdv_id': rdv[0]
            })
        
        conn.commit()
        conn.close()
        return messages
    
    def calculer_prochain_creneau(self, medecin_id, date_rdv, duree_consultation=15):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT heure_rdv FROM rendez_vous 
            WHERE (medecin_generaliste_id = ? OR medecin_specialiste_id = ?)
            AND date_rdv = ?
            AND statut != 'annule'
            AND annule_automatique = 0
            ORDER BY heure_rdv
        ''', (medecin_id, medecin_id, date_rdv))
        rdvs = cursor.fetchall()
        conn.close()
        
        if not rdvs:
            return "08:00"
        
        heures_prises = []
        for rdv in rdvs:
            h, m = map(int, rdv[0].split(':'))
            heures_prises.append(h * 60 + m)
        
        debut_journee = 8 * 60
        fin_journee = 18 * 60
        heures_prises.sort()
        
        for i in range(debut_journee, fin_journee - duree_consultation + 1, duree_consultation):
            disponible = True
            for h in heures_prises:
                if i <= h < i + duree_consultation:
                    disponible = False
                    break
            if disponible:
                return f"{i // 60:02d}:{i % 60:02d}"
        
        # Si plus de créneaux, proposer le lendemain
        return "18:00"


# ==================== UTILS ====================
class TriageMedecin:
    POINTS_SYMPTOMES = {
        'fievre': 1, 'toux': 1, 'douleur_moderee': 2, 'douleur_severe': 5,
        'femme_enceinte': 3, 'difficulte_respiratoire': 8, 'perte_connaissance': 10,
        'hypertension': 3, 'diabete': 2, 'douleur_thoracique': 6, 'vertiges': 3,
        'nausees': 1, 'vomissements': 2, 'hemorragie': 8, 'infection': 2,
        'malaise': 4, 'douleur_abdominale': 3, 'cephalée': 2
    }
    
    @classmethod
    def calculer_score(cls, symptomes_liste):
        score = 0
        symptomes_match = []
        
        for symptome in symptomes_liste:
            symptome_clean = symptome.lower().strip().replace(' ', '_')
            for key, value in cls.POINTS_SYMPTOMES.items():
                if key in symptome_clean or symptome_clean in key:
                    score += value
                    symptomes_match.append(key)
                    break
        
        if score >= 12:
            priorite = 3
            niveau = "URGENCE"
        elif score >= 8:
            priorite = 2
            niveau = "ÉLEVÉE"
        elif score >= 4:
            priorite = 1
            niveau = "MOYENNE"
        else:
            priorite = 0
            niveau = "FAIBLE"
        
        return score, priorite, niveau, symptomes_match
    
    @classmethod
    def orienter_patient(cls, score):
        if score >= 12:
            return "URGENCE", "⚠️ Vos symptômes nécessitent une prise en charge immédiate. Rendez-vous aux urgences."
        else:
            return "CONSULTATION", "✅ Prenez rendez-vous avec un médecin généraliste."
    
    @classmethod
    def suggerer_service(cls, symptomes_liste):
        suggestions = {
            'Cardiologie': ['douleur_thoracique', 'palpitations', 'hypertension', 'cardiaque', 'coeur'],
            'Pneumologie': ['difficulte_respiratoire', 'toux', 'asthme', 'bronchite', 'poumon'],
            'Neurologie': ['perte_connaissance', 'vertiges', 'migraine', 'convulsions', 'tete'],
            'Dermatologie': ['éruption', 'démangeaison', 'rougeur', 'plaie', 'peau'],
            'Gynécologie': ['enceinte', 'regles', 'grossesse', 'femme'],
            'Orthopédie': ['douleur_osseuse', 'fracture', 'entorse', 'dos', 'genou'],
            'Ophtalmologie': ['vision', 'œil', 'yeux', 'vue'],
            'Pédiatrie': ['enfant', 'bébé', 'nourrisson']
        }
        
        for service, mots_cles in suggestions.items():
            for symptome in symptomes_liste:
                symptome_clean = symptome.lower().strip().replace(' ', '_')
                for mot in mots_cles:
                    if mot in symptome_clean or symptome_clean in mot:
                        return service
        return "Généraliste"


# ==================== INIT SESSION ====================
def init_session_state():
    if 'db' not in st.session_state:
        st.session_state.db = Database()
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'page' not in st.session_state:
        st.session_state.page = "Accueil"
    if 'analyse_result' not in st.session_state:
        st.session_state.analyse_result = None
    if 'messages_annulation' not in st.session_state:
        st.session_state.messages_annulation = []


# ==================== PAGES ====================

def page_accueil():
    """Page d'accueil - Point d'entrée unique"""
    st.title("🏥 Système de Gestion des Files d'Attente")
    st.subheader("Bienvenue dans l'application de gestion hospitalière")
    
    # Vérifier les rendez-vous expirés
    messages = st.session_state.db.verifier_et_annuler_rdv_passes()
    if messages:
        for msg in messages:
            st.warning(f"⏰ Rendez-vous de {msg['patient']} du {msg['date']} à {msg['heure']} annulé automatiquement.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 👤 Patient
        
        - Prendre un rendez-vous
        - Consulter ses rendez-vous
        
        """)
        
        if st.button("📋 Prendre rendez-vous", use_container_width=True):
            st.session_state.page = "Patient"
            st.rerun()
        
        if st.button("📅 Voir mes rendez-vous", use_container_width=True):
            st.session_state.page = "Mes rendez-vous"
            st.rerun()
    
    with col2:
        st.markdown("""
        ### 👨‍⚕️ Médecin / Administration
        
        - Se connecter à votre espace
        - Consulter vos patients
        - Gérer les rendez-vous
        
        """)
        
        if st.button("🔐 Se connecter", use_container_width=True):
            st.session_state.page = "Connexion"
            st.rerun()
    
    st.markdown("---")
    
    col3, col4, col5 = st.columns(3)
    
    conn = st.session_state.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM patients")
    nb_patients = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM rendez_vous WHERE annule_automatique = 0")
    nb_rdvs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM rendez_vous WHERE statut = 'en_attente' AND annule_automatique = 0")
    nb_attente = cursor.fetchone()[0]
    conn.close()
    
    with col3:
        st.metric("👤 Patients enregistrés", nb_patients)
    with col4:
        st.metric("📅 Rendez-vous", nb_rdvs)
    with col5:
        st.metric("⏳ En attente", nb_attente)


def page_connexion():
    st.title("🔐 Connexion")
    st.info("💡 Connectez-vous avec vos identifiants médicaux.")
    
    with st.form("connexion_form"):
        email = st.text_input("📧 Email", placeholder="dr.koffi@hopital.com")
        password = st.text_input("🔑 Mot de passe", type="password", placeholder="admin123")
        submitted = st.form_submit_button("Se connecter")
        
        if submitted:
            if not email or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                medecin = st.session_state.db.get_medecin_by_email(email)
                if medecin and medecin[5] == password:
                    st.session_state.logged_in = True
                    st.session_state.user = medecin
                    if medecin[3] == "Administrateur":
                        st.session_state.role = "admin"
                        st.success(f"✅ Bienvenue Administrateur {medecin[2]} {medecin[1]}")
                    else:
                        st.session_state.role = "medecin"
                        st.success(f"✅ Bienvenue Dr. {medecin[2]} {medecin[1]}")
                    st.session_state.page = "Dashboard Medecin"
                    st.rerun()
                else:
                    st.error("❌ Email ou mot de passe incorrect.")
    
    if st.button("← Retour à l'accueil"):
        st.session_state.page = "Accueil"
        st.rerun()


def page_patient():
    """Page patient pour prendre un rendez-vous"""
    st.title("📋 Prendre un rendez-vous")
    
    # --- Analyse des symptômes ---
    with st.form("analyse_form"):
        st.subheader("📝 Vos informations")
        
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom *", placeholder="Votre nom")
            prenom = st.text_input("Prénom *", placeholder="Votre prénom")
            age = st.number_input("Âge *", min_value=0, max_value=150, step=1)
        with col2:
            sexe = st.selectbox("Sexe *", ["", "M", "F"])
            telephone = st.text_input("Téléphone *", placeholder="Ex: 90909090")
            email = st.text_input("Email", placeholder="exemple@email.com")
        
        st.subheader("🩺 Vos symptômes")
        symptomes = st.text_area(
            "Décrivez vos symptômes (séparez par des virgules)",
            placeholder="Ex: fièvre, toux, douleur thoracique, difficulté respiratoire",
            height=100
        )
        
        analyser = st.form_submit_button("🔍 Analyser mes symptômes")
    
    # Traitement de l'analyse
    if analyser and symptomes:
        symptomes_list = [s.strip() for s in symptomes.split(',') if s.strip()]
        if symptomes_list:
            score, priorite, niveau, _ = TriageMedecin.calculer_score(symptomes_list)
            orientation, message = TriageMedecin.orienter_patient(score)
            service_suggere = TriageMedecin.suggerer_service(symptomes_list)
            
            st.session_state.analyse_result = {
                'score': score,
                'priorite': priorite,
                'niveau': niveau,
                'orientation': orientation,
                'message': message,
                'service': service_suggere,
                'symptomes': symptomes_list,
                'nom': nom,
                'prenom': prenom,
                'age': age,
                'sexe': sexe,
                'telephone': telephone,
                'email': email,
                'symptomes_texte': symptomes
            }
            
            st.success("✅ Vos symptômes ont été analysés avec succès.")
            
            if orientation == "URGENCE":
                st.error("⚠️ Pour des raisons de sécurité, nous vous recommandons de consulter rapidement un médecin.")
                st.warning("📞 N'hésitez pas à contacter le service des urgences si vos symptômes s'aggravent.")
            else:
                st.info(f"💡 Un médecin vous a été recommandé. Vous pouvez maintenant prendre un rendez-vous.")
    
    # --- Prise de rendez-vous ---
    if hasattr(st.session_state, 'analyse_result') and st.session_state.analyse_result:
        if st.session_state.analyse_result['orientation'] != "URGENCE":
            st.markdown("---")
            st.subheader("📅 Choisir la date du rendez-vous")
            
            date_rdv = st.date_input(
                "Date du rendez-vous",
                min_value=datetime.now().date(),
                value=datetime.now().date() + timedelta(days=1)
            )
            
            if st.button("📩 Prendre rendez-vous", key="prendre_rdv"):
                result = st.session_state.analyse_result
                
                if not all([result['nom'], result['prenom'], result['age'], result['sexe'], result['telephone']]):
                    st.error("Veuillez remplir tous les champs obligatoires (*).")
                else:
                    # Enregistrer le patient
                    patients = st.session_state.db.get_patient_by_nom_prenom(result['nom'], result['prenom'])
                    if patients:
                        patient_id = patients[0][0]
                    else:
                        patient_id = st.session_state.db.ajouter_patient(
                            result['nom'], result['prenom'], result['age'], 
                            result['sexe'], result['telephone'], result['email'] if result['email'] else None
                        )
                        st.success("✅ Patient enregistré avec succès.")
                    
                    # Trouver le service
                    service_id = None
                    services = st.session_state.db.get_services()
                    for s in services:
                        if s[1] == result['service']:
                            service_id = s[0]
                            break
                    if not service_id:
                        service_id = 1
                    
                    # Trouver un médecin généraliste
                    generalistes = st.session_state.db.get_medecins_by_specialite("Généraliste")
                    if generalistes:
                        medecin_id = generalistes[0][0]
                        duree = generalistes[0][6]
                        heure_proposee = st.session_state.db.calculer_prochain_creneau(
                            medecin_id, date_rdv.strftime("%Y-%m-%d"), duree
                        )
                        
                        if heure_proposee == "18:00":
                            st.warning("⚠️ Aucun créneau disponible pour cette date.")
                        else:
                            st.session_state.db.ajouter_rendez_vous(
                                patient_id=patient_id,
                                service_id=service_id,
                                date_rdv=date_rdv.strftime("%Y-%m-%d"),
                                heure_rdv=heure_proposee,
                                symptomes=result['symptomes_texte'],
                                medecin_generaliste_id=medecin_id,
                                priorite=result['priorite'],
                                score_priorite=result['score']
                            )
                            
                            st.success(f"""
                            ✅ Rendez-vous confirmé !
                            
                            📅 Date: {date_rdv.strftime('%Y-%m-%d')}
                            🕐 Heure: {heure_proposee}
                            🏥 Service: {result['service']}
                            👨‍⚕️ Médecin: Dr. {generalistes[0][2]} {generalistes[0][1]}
                            
                            ℹ️ Veuillez arriver 10 minutes avant l'heure prévue.
                            ⚠️ En cas de retard de plus de 10 minutes, votre rendez-vous sera annulé automatiquement.
                            """)
                            st.balloons()
                            st.session_state.analyse_result = None


def page_mes_rendez_vous():
    """Page pour consulter ses rendez-vous par nom et prénom"""
    st.title("📅 Mes rendez-vous")
    
    st.info("🔍 Entrez votre nom et prénom pour consulter vos rendez-vous.")
    
    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nom *", placeholder="Votre nom")
    with col2:
        prenom = st.text_input("Prénom *", placeholder="Votre prénom")
    
    if st.button("🔍 Rechercher mes rendez-vous"):
        if not nom or not prenom:
            st.warning("Veuillez entrer votre nom et prénom.")
        else:
            patients = st.session_state.db.get_patient_by_nom_prenom(nom, prenom)
            
            if not patients:
                st.error("❌ Aucun patient trouvé avec ce nom et prénom.")
                return
            
            if len(patients) > 1:
                st.warning(f"⚠️ Plusieurs patients trouvés ({len(patients)}). Veuillez préciser.")
                for p in patients:
                    st.info(f"{p[2]} {p[1]} - Téléphone: {p[5]}")
            
            # Prendre le premier patient trouvé
            patient = patients[0]
            rdvs = st.session_state.db.get_rendez_vous_by_patient(patient[0])
            
            if not rdvs:
                st.info("📭 Aucun rendez-vous trouvé pour ce patient.")
            else:
                # Vérifier les rendez-vous expirés
                messages = st.session_state.db.verifier_et_annuler_rdv_passes()
                
                data = []
                for rdv in rdvs:
                    # Vérifier si le rendez-vous a été annulé automatiquement
                    est_annule_auto = rdv[16] if len(rdv) > 16 else 0  # annule_automatique
                    
                    statut_fr = {
                        'en_attente': '⏳ En attente',
                        'confirme': '✅ Confirmé',
                        'annule': '❌ Annulé'
                    }.get(rdv[8], rdv[8])
                    
                    if est_annule_auto == 1:
                        statut_fr = "❌ Annulé (délai dépassé)"
                        rdv_data = {
                            'Date': rdv[5],
                            'Heure': rdv[6],
                            'Service': rdv[-1] if len(rdv) > 15 else 'Généraliste',
                            'Statut': statut_fr,
                            'Message': "⏰ Votre rendez-vous a été annulé car l'heure est dépassée."
                        }
                    else:
                        # Vérifier si le rendez-vous est déjà passé
                        maintenant = datetime.now()
                        date_rdv = datetime.strptime(rdv[5], "%Y-%m-%d")
                        heure_rdv = datetime.strptime(rdv[6], "%H:%M").time()
                        
                        if rdv[8] != 'annule' and (date_rdv < maintenant.date() or 
                           (date_rdv == maintenant.date() and heure_rdv < maintenant.time())):
                            statut_fr = "⚠️ Heure dépassée (en attente d'annulation)"
                            rdv_data = {
                                'Date': rdv[5],
                                'Heure': rdv[6],
                                'Service': rdv[-1] if len(rdv) > 15 else 'Généraliste',
                                'Statut': statut_fr,
                                'Message': "⚠️ L'heure de votre rendez-vous est dépassée. Il sera annulé automatiquement."
                            }
                        else:
                            rdv_data = {
                                'Date': rdv[5],
                                'Heure': rdv[6],
                                'Service': rdv[-1] if len(rdv) > 15 else 'Généraliste',
                                'Statut': statut_fr,
                                'Message': ""
                            }
                    
                    data.append(rdv_data)
                
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
                # Afficher les messages d'alerte pour les rendez-vous annulés
                for item in data:
                    if item['Message']:
                        if "annulé" in item['Message']:
                            st.warning(f"⏰ {item['Message']}")
                        elif "dépassée" in item['Message']:
                            st.info(f"ℹ️ {item['Message']}")


def page_dashboard_medecin():
    if not st.session_state.logged_in:
        st.warning("⚠️ Veuillez vous connecter.")
        return
    
    medecin = st.session_state.user
    st.title(f"👨‍⚕️ Dr. {medecin[2]} {medecin[1]}")
    st.caption(f"Spécialité: {medecin[3]}")
    
    # Vérifier les rendez-vous expirés
    messages = st.session_state.db.verifier_et_annuler_rdv_passes()
    if messages:
        for msg in messages:
            st.warning(f"⏰ Rendez-vous de {msg['patient']} du {msg['date']} à {msg['heure']} annulé automatiquement.")
    
    menu = st.tabs(["📋 Mes patients en attente", "📅 Mon agenda", "👤 Rechercher un patient"])
    
    with menu[0]:
        st.subheader("Mes patients en attente de consultation")
        rdvs = st.session_state.db.get_rendez_vous_by_medecin(medecin[0])
        
        if not rdvs:
            st.info("✅ Aucun patient en attente.")
        else:
            data = []
            for rdv in rdvs:
                if rdv[4] == medecin[0] or rdv[5] == medecin[0]:
                    patient_nom = rdv[-2] if len(rdv) > 16 else "Inconnu"
                    patient_prenom = rdv[-1] if len(rdv) > 16 else ""
                    priorite_fr = {0: 'Faible', 1: 'Moyenne', 2: 'Élevée', 3: 'URGENCE'}.get(rdv[9], 'Faible')
                    
                    # Vérifier si l'heure est dépassée
                    maintenant = datetime.now()
                    date_rdv = datetime.strptime(rdv[5], "%Y-%m-%d")
                    heure_rdv = datetime.strptime(rdv[6], "%H:%M").time()
                    
                    if date_rdv < maintenant.date() or (date_rdv == maintenant.date() and heure_rdv < maintenant.time()):
                        statut = "⚠️ Délai dépassé"
                    else:
                        statut = "En attente"
                    
                    data.append({
                        'ID': rdv[0],
                        'Patient': f"{patient_prenom} {patient_nom}",
                        'Symptômes': rdv[10][:50] + "..." if rdv[10] and len(rdv[10]) > 50 else rdv[10] or 'Non renseignés',
                        'Priorité': priorite_fr,
                        'Date': rdv[5],
                        'Heure': rdv[6],
                        'Statut': statut
                    })
            
            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
                st.subheader("📝 Consultation et orientation")
                rdv_id = st.selectbox("Sélectionnez un patient", 
                                     options=[rdv['ID'] for rdv in data if rdv['Statut'] != "⚠️ Délai dépassé"],
                                     format_func=lambda x: f"{next(r['Patient'] for r in data if r['ID'] == x)} ({r['Heure']})")
                
                if rdv_id:
                    conn = st.session_state.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT r.*, p.nom, p.prenom, p.age, p.sexe, p.telephone 
                        FROM rendez_vous r
                        JOIN patients p ON r.patient_id = p.id
                        WHERE r.id = ?
                    """, (rdv_id,))
                    rdv_data = cursor.fetchone()
                    conn.close()
                    
                    if rdv_data:
                        st.info(f"""
                        **Patient:** {rdv_data[-4]} {rdv_data[-5]}  
                        **Âge:** {rdv_data[-3]} ans  
                        **Sexe:** {rdv_data[-2]}  
                        **Téléphone:** {rdv_data[-1]}  
                        **Symptômes:** {rdv_data[10] if rdv_data[10] else 'Non renseignés'}
                        """)
                        
                        with st.form("consultation_form"):
                            diagnostic = st.text_area("Diagnostic", height=100)
                            service_orientation = st.selectbox(
                                "Orienter vers le service",
                                [s[1] for s in st.session_state.db.get_services()]
                            )
                            submitted = st.form_submit_button("✅ Valider et orienter")
                            
                            if submitted and diagnostic:
                                service_id = None
                                for s in st.session_state.db.get_services():
                                    if s[1] == service_orientation:
                                        service_id = s[0]
                                        break
                                
                                # Calculer un nouveau créneau pour le spécialiste
                                specialistes = st.session_state.db.get_medecins_by_specialite(service_orientation)
                                if specialistes:
                                    specialiste = specialistes[0]
                                    date_rdv = datetime.now().strftime("%Y-%m-%d")
                                    heure_proposee = st.session_state.db.calculer_prochain_creneau(
                                        specialiste[0], date_rdv, specialiste[6]
                                    )
                                    st.session_state.db.update_rendez_vous(
                                        rdv_id,
                                        medecin_specialiste_id=specialiste[0],
                                        service_id=service_id,
                                        diagnostic=diagnostic,
                                        statut='confirme',
                                        date_rdv=date_rdv,
                                        heure_rdv=heure_proposee
                                    )
                                    st.success(f"✅ Patient orienté vers {service_orientation}.")
                                    st.success(f"📅 Nouveau rendez-vous: {date_rdv} à {heure_proposee}")
                                else:
                                    st.session_state.db.update_rendez_vous(
                                        rdv_id,
                                        service_id=service_id,
                                        diagnostic=diagnostic,
                                        statut='confirme'
                                    )
                                    st.success(f"✅ Patient orienté vers {service_orientation}.")
                                st.rerun()
    
    with menu[1]:
        st.subheader("📅 Mon agenda")
        date_agenda = st.date_input("Date", value=datetime.now().date())
        rdvs = st.session_state.db.get_rendez_vous_by_medecin(medecin[0], date_agenda.strftime("%Y-%m-%d"))
        
        if not rdvs:
            st.info("📭 Aucun rendez-vous pour cette date.")
        else:
            data = []
            for rdv in rdvs:
                patient_nom = rdv[-2] if len(rdv) > 16 else "Inconnu"
                patient_prenom = rdv[-1] if len(rdv) > 16 else ""
                service_nom = rdv[-3] if len(rdv) > 16 else "Généraliste"
                statut_fr = {'en_attente': '⏳ En attente', 'confirme': '✅ Confirmé', 'annule': '❌ Annulé'}.get(rdv[8], rdv[8])
                priorite_fr = {0: 'Faible', 1: 'Moyenne', 2: 'Élevée', 3: 'URGENCE'}.get(rdv[9], 'Faible')
                data.append({
                    'Heure': rdv[6],
                    'Patient': f"{patient_prenom} {patient_nom}",
                    'Service': service_nom,
                    'Statut': statut_fr,
                    'Priorité': priorite_fr
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)
    
    with menu[2]:
        st.subheader("🔍 Rechercher un patient")
        col1, col2 = st.columns(2)
        with col1:
            nom_rech = st.text_input("Nom", placeholder="Koffi")
        with col2:
            prenom_rech = st.text_input("Prénom", placeholder="Jean")
        
        if st.button("🔍 Rechercher"):
            if nom_rech or prenom_rech:
                patients = st.session_state.db.get_patient_by_nom_prenom(nom_rech, prenom_rech)
                
                if patients:
                    for p in patients:
                        st.info(f"""
                        **Patient:** {p[2]} {p[1]}  
                        **Âge:** {p[3]} ans  
                        **Sexe:** {p[4]}  
                        **Téléphone:** {p[5]}  
                        **Email:** {p[6] if p[6] else 'Non renseigné'}
                        """)
                else:
                    st.warning("❌ Aucun patient trouvé.")
            else:
                st.warning("Veuillez entrer un nom ou prénom.")
    
    if st.button("🚪 Déconnexion"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.page = "Accueil"
        st.rerun()


def page_dashboard_admin():
    if not st.session_state.logged_in:
        st.warning("⚠️ Veuillez vous connecter.")
        return
    
    admin = st.session_state.user
    st.title(f"👨‍💼 Administration - {admin[2]} {admin[1]}")
    
    # Vérifier les rendez-vous expirés
    messages = st.session_state.db.verifier_et_annuler_rdv_passes()
    if messages:
        for msg in messages:
            st.warning(f"⏰ Rendez-vous de {msg['patient']} du {msg['date']} à {msg['heure']} annulé automatiquement.")
    
    menu = st.tabs(["📊 Vue d'ensemble", "👤 Tous les patients", "📅 Tous les rendez-vous"])
    
    with menu[0]:
        st.subheader("📊 Statistiques globales")
        
        col1, col2, col3, col4 = st.columns(4)
        
        conn = st.session_state.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patients")
        nb_patients = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM rendez_vous WHERE annule_automatique = 0")
        nb_rdvs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM rendez_vous WHERE statut = 'en_attente' AND annule_automatique = 0")
        nb_attente = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM rendez_vous WHERE annule_automatique = 1")
        nb_annules = cursor.fetchone()[0]
        conn.close()
        
        with col1:
            st.metric("👤 Patients", nb_patients)
        with col2:
            st.metric("📅 Rendez-vous", nb_rdvs)
        with col3:
            st.metric("⏳ En attente", nb_attente)
        with col4:
            st.metric("❌ Annulés auto", nb_annules)
        
        conn = st.session_state.db.get_connection()
        df = pd.read_sql_query("""
            SELECT date_rdv, COUNT(*) as nb
            FROM rendez_vous
            WHERE annule_automatique = 0
            GROUP BY date_rdv
            ORDER BY date_rdv
            LIMIT 30
        """, conn)
        conn.close()
        
        if not df.empty:
            st.subheader("📈 Évolution des rendez-vous")
            fig = px.line(df, x='date_rdv', y='nb', title='Rendez-vous par jour')
            st.plotly_chart(fig, use_container_width=True)
    
    with menu[1]:
        st.subheader("👤 Tous les patients")
        col1, col2 = st.columns(2)
        with col1:
            nom_rech = st.text_input("Nom", placeholder="Koffi")
        with col2:
            prenom_rech = st.text_input("Prénom", placeholder="Jean")
        
        conn = st.session_state.db.get_connection()
        cursor = conn.cursor()
        if nom_rech or prenom_rech:
            cursor.execute("""
                SELECT * FROM patients 
                WHERE nom LIKE ? AND prenom LIKE ?
                ORDER BY nom
            """, (f"%{nom_rech}%", f"%{prenom_rech}%"))
        else:
            cursor.execute("SELECT * FROM patients ORDER BY nom")
        patients = cursor.fetchall()
        conn.close()
        
        if patients:
            data = []
            for p in patients:
                data.append({
                    'ID': p[0],
                    'Nom': p[1],
                    'Prénom': p[2],
                    'Âge': p[3],
                    'Sexe': p[4],
                    'Téléphone': p[5],
                    'Email': p[6] if p[6] else 'N/A'
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info("📭 Aucun patient trouvé.")
    
    with menu[2]:
        st.subheader("📅 Tous les rendez-vous")
        rdvs = st.session_state.db.get_all_rendez_vous()
        
        if rdvs:
            data = []
            for rdv in rdvs:
                patient_nom = rdv[-2] if len(rdv) > 16 else "Inconnu"
                patient_prenom = rdv[-1] if len(rdv) > 16 else ""
                service_nom = rdv[-3] if len(rdv) > 16 else "Généraliste"
                statut_fr = {'en_attente': '⏳ En attente', 'confirme': '✅ Confirmé', 'annule': '❌ Annulé'}.get(rdv[8], rdv[8])
                priorite_fr = {0: 'Faible', 1: 'Moyenne', 2: 'Élevée', 3: 'URGENCE'}.get(rdv[9], 'Faible')
                annule_auto = "✅" if rdv[16] == 1 else "❌"
                data.append({
                    'ID': rdv[0],
                    'Patient': f"{patient_prenom} {patient_nom}",
                    'Date': rdv[5],
                    'Heure': rdv[6],
                    'Service': service_nom,
                    'Statut': statut_fr,
                    'Priorité': priorite_fr,
                    'Annulé auto': annule_auto
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info("📭 Aucun rendez-vous trouvé.")
    
    if st.button("🚪 Déconnexion"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.page = "Accueil"
        st.rerun()


# ==================== MAIN ====================
def main():
    init_session_state()
    
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/4325/4325546.png", width=60)
        st.title("🏥 Gestion Hospitalière")
        st.markdown("---")
        
        if st.session_state.logged_in:
            role = "Administrateur" if st.session_state.role == "admin" else "Médecin"
            st.success(f"👨‍⚕️ {role}: {st.session_state.user[2]} {st.session_state.user[1]}")
            st.markdown("---")
        
        if st.session_state.logged_in:
            if st.session_state.role == "admin":
                if st.button("📊 Administration"):
                    st.session_state.page = "Dashboard Admin"
                    st.rerun()
            else:
                if st.button("👨‍⚕️ Mes patients"):
                    st.session_state.page = "Dashboard Medecin"
                    st.rerun()
        else:
            if st.button("🏠 Accueil"):
                st.session_state.page = "Accueil"
                st.rerun()
            if st.button("📋 Prendre rendez-vous"):
                st.session_state.page = "Patient"
                st.rerun()
            if st.button("📅 Mes rendez-vous"):
                st.session_state.page = "Mes rendez-vous"
                st.rerun()
            if st.button("🔐 Se connecter"):
                st.session_state.page = "Connexion"
                st.rerun()
        
        st.markdown("---")
        st.caption("© 2026 - Projet PHY330")
        st.caption("Version 3.0")
    
    if st.session_state.logged_in:
        if st.session_state.role == "admin":
            if st.session_state.page == "Dashboard Admin":
                page_dashboard_admin()
            else:
                st.session_state.page = "Dashboard Admin"
                page_dashboard_admin()
        else:
            if st.session_state.page == "Dashboard Medecin":
                page_dashboard_medecin()
            else:
                st.session_state.page = "Dashboard Medecin"
                page_dashboard_medecin()
    else:
        if st.session_state.page == "Patient":
            page_patient()
        elif st.session_state.page == "Mes rendez-vous":
            page_mes_rendez_vous()
        elif st.session_state.page == "Connexion":
            page_connexion()
        else:
            page_accueil()


if __name__ == "__main__":
    main()
