# app_streamlit.py - Application Hospitalière avec Streamlit
import streamlit as st
import sqlite3
import os
import re
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
    def __init__(self, db_path="data/hopital.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.init_tables()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                FOREIGN KEY (medecin_generaliste_id) REFERENCES medecins(id),
                FOREIGN KEY (medecin_specialiste_id) REFERENCES medecins(id),
                FOREIGN KEY (service_id) REFERENCES services(id)
            )
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM medecins")
        if cursor.fetchone()[0] == 0:
            medecins = [
                ("Koffi", "Jean", "Généraliste", "dr.koffi@hopital.com", "admin123", 15),
                ("Amadou", "Moussa", "Cardiologue", "dr.amadou@hopital.com", "admin123", 20),
                ("Ade", "Yvette", "Gynécologue", "dr.ade@hopital.com", "admin123", 20),
                ("Komi", "Pierre", "Pédiatre", "dr.komi@hopital.com", "admin123", 15)
            ]
            cursor.executemany('''
                INSERT INTO medecins (nom, prenom, specialite, email, mot_de_passe, duree_consultation)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', medecins)
        
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
    
    def ajouter_patient(self, nom, prenom, age, sexe, telephone, email=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO patients (nom, prenom, age, sexe, telephone, email)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nom, prenom, age, sexe, telephone, email))
        patient_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return patient_id
    
    def get_patient_by_telephone(self, telephone):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE telephone = ?", (telephone,))
        patient = cursor.fetchone()
        conn.close()
        return patient
    
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
    
    def calculer_prochain_creneau(self, medecin_id, date_rdv, duree_consultation=15):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT heure_rdv FROM rendez_vous 
            WHERE (medecin_generaliste_id = ? OR medecin_specialiste_id = ?)
            AND date_rdv = ?
            AND statut != 'annule'
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


# ==================== STREAMLIT APP ====================
def init_session_state():
    """Initialise les variables de session"""
    if 'db' not in st.session_state:
        st.session_state.db = Database()
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = "Accueil"
    if 'patient_telephone' not in st.session_state:
        st.session_state.patient_telephone = ""


# ==================== PAGES ====================
def page_accueil():
    """Page d'accueil"""
    st.title("🏥 Système Intelligent de Gestion des Files d'Attente")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 👤 Patient
        - Prenez un rendez-vous en ligne
        - Consultez vos rendez-vous
        - Recevez votre heure d'arrivée
        """)
        if st.button("📋 Prendre rendez-vous", use_container_width=True):
            st.session_state.page = "Patient"
            st.rerun()
    
    with col2:
        st.markdown("""
        ### 👨‍⚕️ Médecin
        - Consultez les patients en attente
        - Posez un diagnostic
        - Orientez vers un spécialiste
        """)
        if st.button("🔐 Se connecter", use_container_width=True):
            st.session_state.page = "Connexion"
            st.rerun()
    
    with col3:
        st.markdown("""
        ### 📊 Statistiques
        - Nombre de patients
        - Rendez-vous par jour
        - Services les plus demandés
        """)
        if st.button("📊 Voir les stats", use_container_width=True):
            st.session_state.page = "Statistiques"
            st.rerun()


def page_connexion():
    """Page de connexion médecin"""
    st.title("🔐 Connexion Médecin")
    
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
                    st.success(f"✅ Bienvenue Dr. {medecin[2]} {medecin[1]}")
                    st.rerun()
                else:
                    st.error("❌ Email ou mot de passe incorrect.")
    
    if st.button("← Retour à l'accueil"):
        st.session_state.page = "Accueil"
        st.rerun()

def page_patient():
    """Page patient pour prendre rendez-vous"""
    st.title("📋 Prendre un rendez-vous")
    
    tab1, tab2 = st.tabs(["📝 Nouveau rendez-vous", "📅 Mes rendez-vous"])
    
    with tab1:
        with st.form("rdv_form"):
            st.subheader("Informations personnelles")
            
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nom *", placeholder="Votre nom")
                prenom = st.text_input("Prénom *", placeholder="Votre prénom")
                age = st.number_input("Âge *", min_value=0, max_value=150, step=1)
            with col2:
                sexe = st.selectbox("Sexe *", ["", "M", "F"])
                telephone = st.text_input("Téléphone *", placeholder="Ex: 90909090")
                email = st.text_input("Email", placeholder="exemple@email.com")
            
            st.subheader("Symptômes")
            symptomes = st.text_area(
                "Décrivez vos symptômes (séparez par des virgules)",
                placeholder="Ex: fièvre, toux, douleur thoracique, difficulté respiratoire",
                height=100
            )
            
            analyse_btn = st.form_submit_button("🔍 Analyser mes symptômes")
        
        # Analyse des symptômes
        if analyse_btn and symptomes:
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
                    'symptomes': symptomes_list
                }
                
                # ✅ AFFICHAGE NEUTRE - Sans mention du score ou de la priorité
                st.success("✅ Vos symptômes ont été analysés avec succès.")
                
                if orientation == "URGENCE":
                    st.error("⚠️ Pour des raisons de sécurité, nous vous recommandons de consulter rapidement un médecin.")
                    st.warning("📞 N'hésitez pas à contacter le service des urgences si vos symptômes s'aggravent.")
                else:
                    st.info(f"💡 Un médecin {service_suggere} vous a été recommandé. Vous pouvez maintenant prendre un rendez-vous.")
        
        # Prise de rendez-vous
        if hasattr(st.session_state, 'analyse_result') and st.session_state.analyse_result:
            if st.session_state.analyse_result['orientation'] != "URGENCE":
                st.subheader("📅 Choisir la date du rendez-vous")
                
                date_rdv = st.date_input(
                    "Date du rendez-vous",
                    min_value=datetime.now().date(),
                    value=datetime.now().date() + timedelta(days=1)
                )
                
                if st.button("📩 Prendre rendez-vous"):
                    if not all([nom, prenom, age, sexe, telephone]):
                        st.error("Veuillez remplir tous les champs obligatoires (*).")
                    else:
                        patient = st.session_state.db.get_patient_by_telephone(telephone)
                        if patient:
                            patient_id = patient[0]
                        else:
                            patient_id = st.session_state.db.ajouter_patient(
                                nom, prenom, age, sexe, telephone, email if email else None
                            )
                            st.success("✅ Patient enregistré avec succès.")
                        
                        service_id = None
                        services = st.session_state.db.get_services()
                        for s in services:
                            if s[1] == st.session_state.analyse_result['service']:
                                service_id = s[0]
                                break
                        if not service_id:
                            service_id = 1
                        
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
                                rdv_id = st.session_state.db.ajouter_rendez_vous(
                                    patient_id=patient_id,
                                    service_id=service_id,
                                    date_rdv=date_rdv.strftime("%Y-%m-%d"),
                                    heure_rdv=heure_proposee,
                                    symptomes=symptomes,
                                    medecin_generaliste_id=medecin_id,
                                    priorite=st.session_state.analyse_result['priorite'],
                                    score_priorite=st.session_state.analyse_result['score']
                                )
                                
                                # ✅ CONFIRMATION SANS PRIORITÉ
                                st.success(f"""
                                ✅ Rendez-vous confirmé !
                                
                                📅 Date: {date_rdv.strftime('%Y-%m-%d')}
                                🕐 Heure: {heure_proposee}
                                🏥 Service: {st.session_state.analyse_result['service']}
                                👨‍⚕️ Médecin: Dr. {generalistes[0][2]} {generalistes[0][1]}
                                
                                ℹ️ Veuillez arriver 10 minutes avant l'heure prévue.
                                ⚠️ En cas de retard de plus de 10 minutes, votre rendez-vous sera annulé.
                                """)
                                st.balloons()
                                st.session_state.analyse_result = None
                        else:
                            st.error("❌ Aucun médecin généraliste disponible.")
    
    with tab2:
        st.subheader("🔍 Consulter mes rendez-vous")
        telephone_rech = st.text_input("Entrez votre numéro de téléphone", 
                                      placeholder="Ex: 90909090")
        if st.button("🔍 Rechercher"):
            if telephone_rech:
                patient = st.session_state.db.get_patient_by_telephone(telephone_rech)
                if patient:
                    rdvs = st.session_state.db.get_rendez_vous_by_patient(patient[0])
                    if rdvs:
                        data = []
                        for rdv in rdvs:
                            statut_fr = {
                                'en_attente': '⏳ En attente',
                                'confirme': '✅ Confirmé',
                                'annule': '❌ Annulé',
                                'termine': '✅ Terminé'
                            }.get(rdv[8], rdv[8])
                            # ✅ PRIORITÉ SUPPRIMÉE pour le patient
                            data.append({
                                'Date': rdv[5],
                                'Heure': rdv[6],
                                'Service': rdv[-1] if len(rdv) > 15 else 'Généraliste',
                                'Statut': statut_fr
                                # 'Priorité' : SUPPRIMÉ
                            })
                        st.dataframe(pd.DataFrame(data), use_container_width=True)
                    else:
                        st.info("📭 Aucun rendez-vous trouvé.")
                else:
                    st.error("❌ Aucun patient trouvé avec ce numéro.")
            else:
                st.warning("Veuillez entrer un numéro de téléphone.")


def page_medecin():
    """Page médecin"""
    if not st.session_state.logged_in:
        st.warning("⚠️ Veuillez vous connecter d'abord.")
        if st.button("🔐 Se connecter"):
            st.session_state.page = "Connexion"
            st.rerun()
        return
    
    medecin = st.session_state.user
    st.title(f"👨‍⚕️ Dr. {medecin[2]} {medecin[1]}")
    st.caption(f"Spécialité: {medecin[3]}")
    
    tab1, tab2 = st.tabs(["📋 Patients en attente", "📅 Mon agenda"])
    
    with tab1:
        st.subheader("Patients en attente de consultation")
        
        rdvs = st.session_state.db.get_rendez_vous_en_attente()
        
        if not rdvs:
            st.info("✅ Aucun patient en attente.")
        else:
            data = []
            for rdv in rdvs:
                patient_nom = rdv[-2] if len(rdv) > 16 else "Inconnu"
                patient_prenom = rdv[-1] if len(rdv) > 16 else ""
                priorite_fr = {0: 'Faible', 1: 'Moyenne', 2: 'Élevée', 3: 'URGENCE'}.get(rdv[9], 'Faible')
                data.append({
                    'ID': rdv[0],
                    'Patient': f"{patient_prenom} {patient_nom}",
                    'Symptômes': rdv[10][:50] + "..." if rdv[10] and len(rdv[10]) > 50 else rdv[10] or 'Non renseignés',
                    'Score': rdv[10],
                    'Priorité': priorite_fr,
                    'Date': rdv[5],
                    'Heure': rdv[6]
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=300)
            
            # Consultation
            st.subheader("📝 Consultation et orientation")
            rdv_id = st.selectbox("Sélectionnez un patient à consulter", 
                                  options=[rdv['ID'] for rdv in data],
                                  format_func=lambda x: f"{next(r['Patient'] for r in data if r['ID'] == x)} ({x})")
            
            if rdv_id:
                rdv = st.session_state.db.get_rendez_vous_by_patient(rdv_id)
                if rdv:
                    rdv_data = rdv[0] if isinstance(rdv, list) else rdv
                    patient = st.session_state.db.get_patient_by_id(rdv_data[1]) if rdv_data else None
                    
                    if patient:
                        st.info(f"""
                        **Patient:** {patient[2]} {patient[1]}  
                        **Âge:** {patient[3]} ans  
                        **Sexe:** {patient[4]}  
                        **Téléphone:** {patient[5]}  
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
                            # Récupérer l'ID du service
                            service_id = None
                            for s in st.session_state.db.get_services():
                                if s[1] == service_orientation:
                                    service_id = s[0]
                                    break
                            
                            # Trouver un spécialiste
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
                                st.success(f"""
                                ✅ Patient orienté vers {service_orientation}
                                👨‍⚕️ Dr. {specialiste[2]} {specialiste[1]}
                                📅 Date: {date_rdv}
                                🕐 Heure: {heure_proposee}
                                """)
                                st.rerun()
                            else:
                                st.session_state.db.update_rendez_vous(
                                    rdv_id,
                                    service_id=service_id,
                                    diagnostic=diagnostic,
                                    statut='confirme'
                                )
                                st.success(f"✅ Patient orienté vers {service_orientation}.")
                                st.rerun()
    
    with tab2:
        st.subheader("📅 Mon agenda")
        date_agenda = st.date_input("Date", value=datetime.now().date())
        rdvs = st.session_state.db.get_rendez_vous_by_medecin(
            medecin[0], date_agenda.strftime("%Y-%m-%d")
        )
        
        if not rdvs:
            st.info("📭 Aucun rendez-vous pour cette date.")
        else:
            data = []
            for rdv in rdvs:
                patient_nom = rdv[-2] if len(rdv) > 16 else "Inconnu"
                patient_prenom = rdv[-1] if len(rdv) > 16 else ""
                service_nom = rdv[-3] if len(rdv) > 16 else "Généraliste"
                statut_fr = {
                    'en_attente': '⏳ En attente',
                    'confirme': '✅ Confirmé',
                    'annule': '❌ Annulé',
                    'termine': '✅ Terminé'
                }.get(rdv[8], rdv[8])
                priorite_fr = {
                    0: 'Faible', 1: 'Moyenne', 2: 'Élevée', 3: 'URGENCE'
                }.get(rdv[9], 'Faible')
                data.append({
                    'Heure': rdv[6],
                    'Patient': f"{patient_prenom} {patient_nom}",
                    'Service': service_nom,
                    'Statut': statut_fr,
                    'Priorité': priorite_fr
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)


def page_statistiques():
    """Page des statistiques"""
    st.title("📊 Statistiques Hospitalières")
    
    db = st.session_state.db
    
    # Statistiques générales
    col1, col2, col3, col4 = st.columns(4)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM patients")
    nb_patients = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM rendez_vous")
    nb_rdvs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM rendez_vous WHERE statut = 'en_attente'")
    nb_attente = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM rendez_vous WHERE statut = 'confirme'")
    nb_confirme = cursor.fetchone()[0]
    conn.close()
    
    with col1:
        st.metric("👤 Patients", nb_patients)
    with col2:
        st.metric("📅 Rendez-vous", nb_rdvs)
    with col3:
        st.metric("⏳ En attente", nb_attente, delta="-25%")
    with col4:
        st.metric("✅ Confirmés", nb_confirme, delta="+12%")
    
    # Graphique des rendez-vous par jour
    conn = db.get_connection()
    df = pd.read_sql_query("""
        SELECT date_rdv, COUNT(*) as nb
        FROM rendez_vous
        GROUP BY date_rdv
        ORDER BY date_rdv
        LIMIT 30
    """, conn)
    conn.close()
    
    if not df.empty:
        st.subheader("📈 Rendez-vous par jour")
        fig = px.line(df, x='date_rdv', y='nb', 
                     title='Évolution des rendez-vous',
                     labels={'date_rdv': 'Date', 'nb': 'Nombre de rendez-vous'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Répartition par service
    conn = db.get_connection()
    df_services = pd.read_sql_query("""
        SELECT s.nom, COUNT(r.id) as nb
        FROM rendez_vous r
        LEFT JOIN services s ON r.service_id = s.id
        GROUP BY s.nom
        ORDER BY nb DESC
    """, conn)
    conn.close()
    
    if not df_services.empty:
        st.subheader("🏥 Répartition par service")
        fig = px.pie(df_services, values='nb', names='nom',
                    title='Rendez-vous par service')
        st.plotly_chart(fig, use_container_width=True)


# ==================== MAIN ====================
def main():
    """Fonction principale de l'application"""
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/4325/4325546.png", width=80)
        st.title("🏥 Gestion Hospitalière")
        st.markdown("---")
        
        if st.session_state.logged_in:
            st.success(f"👨‍⚕️ Dr. {st.session_state.user[2]}")
            if st.button("🚪 Déconnexion"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.page = "Accueil"
                st.rerun()
        
        st.markdown("---")
        if st.button("🏠 Accueil"):
            st.session_state.page = "Accueil"
            st.rerun()
        if st.button("📋 Patient"):
            st.session_state.page = "Patient"
            st.rerun()
        if st.button("🔐 Médecin"):
            st.session_state.page = "Connexion"
            st.rerun()
        if st.button("📊 Statistiques"):
            st.session_state.page = "Statistiques"
            st.rerun()
        
        st.markdown("---")
        st.caption("© 2026 - Projet PHY330")
        st.caption("Version 1.0")
    
    # Pages
    if st.session_state.logged_in and st.session_state.page != "Accueil":
        if st.session_state.page == "Patient":
            page_patient()
        elif st.session_state.page == "Connexion":
            page_connexion()
        elif st.session_state.page == "Statistiques":
            page_statistiques()
        else:
            page_medecin()
    else:
        if st.session_state.page == "Patient":
            page_patient()
        elif st.session_state.page == "Connexion":
            page_connexion()
        elif st.session_state.page == "Statistiques":
            page_statistiques()
        else:
            page_accueil()


if __name__ == "__main__":
    main()
