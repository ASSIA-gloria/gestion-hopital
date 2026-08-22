import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import re

# ============================================
# CONFIGURATION DE LA PAGE
# ============================================
st.set_page_config(
    page_title="Gestion Hospitalière Intelligente",
    page_icon="🏥",
    layout="wide"
)

# ============================================
# BASE DE DONNÉES (en mémoire)
# ============================================

# Dictionnaire de correspondance symptômes → service
SYMPTONE_TO_SERVICE = {
    # Cardiologie
    "douleur thoracique": "cardiologie",
    "essoufflement": "cardiologie",
    "palpitations": "cardiologie",
    "cardiaque": "cardiologie",
    "poitrine": "cardiologie",
    
    # Pneumologie
    "toux": "pneumologie",
    "crachat": "pneumologie",
    "expectoration": "pneumologie",
    "respiration": "pneumologie",
    "asthme": "pneumologie",
    
    # Neurologie
    "mal de tête": "neurologie",
    "migraine": "neurologie",
    "vertige": "neurologie",
    "perte de connaissance": "neurologie",
    "paralysie": "neurologie",
    "avc": "neurologie",
    
    # Gynécologie
    "règle": "gynecologie",
    "menstruation": "gynecologie",
    "grossesse": "gynecologie",
    "accouchement": "gynecologie",
    "utérus": "gynecologie",
    "ovaires": "gynecologie",
    
    # Dermatologie
    "éruption": "dermatologie",
    "démangeaison": "dermatologie",
    "bouton": "dermatologie",
    "peau": "dermatologie",
    "plaque": "dermatologie",
    
    # Gastro-entérologie
    "ventre": "gastro-enterologie",
    "estomac": "gastro-enterologie",
    "nausée": "gastro-enterologie",
    "vomissement": "gastro-enterologie",
    "diarrhée": "gastro-enterologie",
    "constipation": "gastro-enterologie",
    
    # Urologie
    "urine": "urologie",
    "rénal": "urologie",
    "rein": "urologie",
    "vessie": "urologie",
    
    # Ophtalmologie
    "œil": "ophtalmologie",
    "vue": "ophtalmologie",
    "vision": "ophtalmologie",
    
    # ORL
    "oreille": "orl",
    "nez": "orl",
    "gorge": "orl",
    "audition": "orl",
}

# Barème de points pour les symptômes
SYMPTOME_POINTS = {
    "douleur thoracique": 4,
    "essoufflement": 3,
    "perte de connaissance": 5,
    "paralysie": 5,
    "avc": 5,
    "hémorragie": 5,
    "fracture": 4,
    "fièvre": 3,
    "vomissement": 2,
    "diarrhée": 2,
    "démangeaison": 1,
    "éruption": 1,
    "toux": 1,
    "mal de tête": 2,
    "vertige": 2,
    "palpitations": 3,
}

# Liste des médecins avec leurs spécialités et plannings
MEDECINS = {
    "Dr. Martin": {
        "specialite": "medecine generale",
        "heures": (8, 16),  # 8h - 16h
        "consultation_duree": 15,  # minutes
        "creneaux_urgence": [2, 5, 8, 11],  # index des créneaux réservés pour urgences
        "planning": {}  # sera rempli dynamiquement
    },
    "Dr. Diallo": {
        "specialite": "medecine generale",
        "heures": (9, 17),
        "consultation_duree": 15,
        "creneaux_urgence": [3, 7, 10],
        "planning": {}
    },
    "Dr. Kone": {
        "specialite": "cardiologie",
        "heures": (8, 14),
        "consultation_duree": 20,
        "creneaux_urgence": [1, 4, 7],
        "planning": {}
    },
    "Dr. Bamba": {
        "specialite": "pediatrie",
        "heures": (10, 18),
        "consultation_duree": 15,
        "creneaux_urgence": [2, 6, 9],
        "planning": {}
    },
    "Dr. Touré": {
        "specialite": "dermatologie",
        "heures": (8, 12),
        "consultation_duree": 15,
        "creneaux_urgence": [2, 5],
        "planning": {}
    },
    "Dr. Kouadio": {
        "specialite": "gynecologie",
        "heures": (13, 19),
        "consultation_duree": 20,
        "creneaux_urgence": [2, 6, 9],
        "planning": {}
    },
}

# ============================================
# FONCTIONS DE TRAITEMENT
# ============================================

def analyser_symptomes(texte):
    """
    Analyse les symptômes saisis par le patient
    Retourne: service_deduit, score_priorite, symptomes_detectes
    """
    texte_lower = texte.lower()
    mots = re.findall(r'\b\w+\b', texte_lower)
    
    # Détection des symptômes et calcul du score
    symptomes_detectes = []
    score = 0
    
    for symptome, points in SYMPTOME_POINTS.items():
        if symptome in texte_lower:
            symptomes_detectes.append(symptome)
            score += points
    
    # Détection du service
    service_deduit = "medecine generale"  # par défaut
    service_score = {}
    
    for symptome in symptomes_detectes:
        for mot_cle, service in SYMPTONE_TO_SERVICE.items():
            if symptome == mot_cle or mot_cle in symptome:
                if service not in service_score:
                    service_score[service] = 0
                service_score[service] += SYMPTOME_POINTS.get(symptome, 1)
    
    # Choisir le service avec le score le plus élevé
    if service_score:
        service_deduit = max(service_score, key=service_score.get)
    
    # Classification du score
    if score <= 3:
        priorite = "Faible"
    elif score <= 7:
        priorite = "Moyenne"
    elif score <= 12:
        priorite = "Élevée"
    else:
        priorite = "URGENCE"
    
    return service_deduit, score, priorite, symptomes_detectes


def trouver_medecin_disponible(service, date_consultation, est_urgent=False):
    """
    Trouve le médecin le plus disponible pour un service donné
    """
    medecins_disponibles = []
    
    for nom, infos in MEDECINS.items():
        # Vérifier si le médecin correspond au service ou est généraliste
        if infos["specialite"] == service or infos["specialite"] == "medecine generale":
            medecins_disponibles.append(nom)
    
    if not medecins_disponibles:
        return None
    
    # Si c'est une urgence, chercher le médecin avec le plus de créneaux libres
    if est_urgent:
        # Priorité aux médecins avec des créneaux d'urgence disponibles
        for nom in medecins_disponibles:
            infos = MEDECINS[nom]
            if len(infos["planning"]) < 10:  # capacité raisonnable
                return nom
    
    # Sinon, équilibrage de charge
    charge_min = float('inf')
    medecin_choisi = medecins_disponibles[0]
    
    for nom in medecins_disponibles:
        charge = len(MEDECINS[nom]["planning"])
        if charge < charge_min:
            charge_min = charge
            medecin_choisi = nom
    
    return medecin_choisi


def attribuer_heure(medecin_nom, est_urgent=False):
    """
    Attribue une heure de rendez-vous pour un médecin donné
    """
    infos = MEDECINS[medecin_nom]
    heure_debut, heure_fin = infos["heures"]
    duree = infos["consultation_duree"]
    planning = infos["planning"]
    creneaux_urgence = infos["creneaux_urgence"]
    
    # Générer tous les créneaux possibles
    creneaux = []
    heure_courante = datetime.now().replace(hour=heure_debut, minute=0, second=0, microsecond=0)
    heure_fin_datetime = datetime.now().replace(hour=heure_fin, minute=0, second=0, microsecond=0)
    
    index = 0
    while heure_courante < heure_fin_datetime:
        if est_urgent and index in creneaux_urgence:
            # Créneau réservé pour les urgences
            creneaux.append(heure_courante)
        elif not est_urgent and index not in creneaux_urgence:
            # Créneau pour les consultations normales
            creneaux.append(heure_courante)
        
        heure_courante += timedelta(minutes=duree)
        index += 1
    
    # Filtrer les créneaux déjà pris
    creneaux_disponibles = [c for c in creneaux if c not in planning.values()]
    
    if not creneaux_disponibles:
        return None
    
    # Prendre le premier créneau disponible
    heure_rdv = creneaux_disponibles[0]
    
    # Ajouter au planning du médecin
    planning[len(planning)] = heure_rdv
    
    return heure_rdv


def gerer_retard(heure_rdv, heure_arrivee):
    """
    Gère les retards des patients
    """
    if heure_arrivee is None:
        return "Rendez-vous confirmé"
    
    retard = (heure_arrivee - heure_rdv).total_seconds() / 60  # en minutes
    
    if retard <= 10:
        return f"Retard de {int(retard)} minutes. Vous serez reçu normalement."
    else:
        # Ajouter en fin de file
        return f"⚠️ Retard de {int(retard)} minutes. Rendez-vous annulé. Vous êtes replacé en fin de file."


# ============================================
# INTERFACE STREAMLIT
# ============================================

st.title("🏥 Système Intelligent de Gestion Hospitalière")
st.markdown("---")

# Initialisation de l'état de session
if 'patient_inscrit' not in st.session_state:
    st.session_state.patient_inscrit = False
    st.session_state.rdv_attribue = False
    st.session_state.historique = []
    st.session_state.nb_patients = 0

# Sidebar - Informations générales
with st.sidebar:
    st.header("📊 Tableau de bord")
    st.metric("👥 Patients enregistrés aujourd'hui", st.session_state.nb_patients)
    
    st.markdown("---")
    st.subheader("👨‍⚕️ Médecins disponibles")
    for nom, infos in MEDECINS.items():
        nb_consultations = len(infos["planning"])
        specialite = infos["specialite"].upper()
        st.write(f"**{nom}** ({specialite}) - {nb_consultations} patients")

# ============================================
# SECTION INSCRIPTION PATIENT
# ============================================

st.header("📝 Inscription à distance")

if not st.session_state.patient_inscrit:
    with st.form("inscription_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nom = st.text_input("Nom complet *", placeholder="Ex: Jean Dupont")
            age = st.number_input("Âge *", min_value=0, max_value=120, step=1)
            telephone = st.text_input("Téléphone *", placeholder="Ex: 0102030405")
        
        with col2:
            sexe = st.selectbox("Sexe *", ["", "Homme", "Femme", "Autre"])
            email = st.text_input("Email", placeholder="exemple@email.com")
        
        st.markdown("---")
        st.subheader("🩺 Décrivez vos symptômes")
        
        symptomes = st.text_area(
            "Décrivez précisément vos symptômes",
            placeholder="Ex: J'ai mal à la poitrine, je suis essoufflé et j'ai de la fièvre...",
            height=100
        )
        
        st.caption("⚠️ Le système analysera automatiquement vos symptômes pour vous orienter vers le bon service.")
        
        submitted = st.form_submit_button("📤 Envoyer ma demande")
        
        if submitted:
            if not nom or not age or not telephone or not symptomes:
                st.error("Veuillez remplir tous les champs obligatoires (*)")
            else:
                # Analyse des symptômes
                service, score, priorite, symptomes_detectes = analyser_symptomes(symptomes)
                
                # Déterminer si c'est une urgence
                est_urgent = priorite == "URGENCE"
                
                # Vérifier les red flags absolus
                red_flags = ["douleur thoracique", "perte de connaissance", "paralysie", "avc", "hémorragie"]
                red_flag_detecte = any(flag in symptomes.lower() for flag in red_flags)
                
                if red_flag_detecte or est_urgent:
                    st.warning("🚨 **URGENCE DÉTECTÉE !** Rendez-vous immédiatement aux urgences.")
                    st.info(f"Score: {score} - {priorite}")
                    st.stop()
                
                # Trouver un médecin disponible
                medecin = trouver_medecin_disponible(service, datetime.now(), est_urgent)
                
                if not medecin:
                    st.error("Aucun médecin disponible pour ce service. Veuillez réessayer plus tard.")
                    st.stop()
                
                # Attribuer une heure
                heure_rdv = attribuer_heure(medecin, est_urgent)
                
                if not heure_rdv:
                    st.error("Aucun créneau disponible. Veuillez réessayer plus tard.")
                    st.stop()
                
                # Enregistrer le patient
                st.session_state.patient_inscrit = True
                st.session_state.rdv_attribue = True
                st.session_state.nb_patients += 1
                
                patient_info = {
                    "nom": nom,
                    "age": age,
                    "sexe": sexe,
                    "telephone": telephone,
                    "email": email,
                    "symptomes": symptomes,
                    "service": service,
                    "score": score,
                    "priorite": priorite,
                    "medecin": medecin,
                    "heure_rdv": heure_rdv,
                    "symptomes_detectes": symptomes_detectes,
                    "est_urgent": est_urgent
                }
                
                st.session_state.historique.append(patient_info)
                st.session_state.patient_courant = patient_info
                
                st.success("✅ Votre demande a été enregistrée avec succès !")
                st.rerun()

# ============================================
# AFFICHAGE DU RÉSULTAT
# ============================================

if st.session_state.rdv_attribue and hasattr(st.session_state, 'patient_courant'):
    patient = st.session_state.patient_courant
    
    st.markdown("---")
    st.header("✅ Rendez-vous confirmé")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Informations patient")
        st.write(f"**Nom:** {patient['nom']}")
        st.write(f"**Âge:** {patient['age']} ans")
        st.write(f"**Sexe:** {patient['sexe']}")
        st.write(f"**Téléphone:** {patient['telephone']}")
    
    with col2:
        st.subheader("📋 Résultats de l'analyse")
        st.write(f"**Service:** {patient['service'].upper()}")
        st.write(f"**Score clinique:** {patient['score']}")
        st.write(f"**Priorité:** {patient['priorite']}")
        st.write(f"**Médecin:** {patient['medecin']}")
    
    st.markdown("---")
    
    # Heure de rendez-vous
    st.subheader("🕐 Votre rendez-vous")
    heure_formatee = patient['heure_rdv'].strftime("%H:%M")
    heure_arrivee = (patient['heure_rdv'] - timedelta(minutes=10)).strftime("%H:%M")
    
    st.success(f"""
    ### 📅 Votre consultation est prévue à **{heure_formatee}**
    
    ⚠️ **Arrivez à {heure_arrivee}** (10 minutes avant)
    
    📍 **Service:** {patient['service'].upper()}
    👨‍⚕️ **Médecin:** {patient['medecin']}
    """)
    
    # Symptômes détectés
    if patient['symptomes_detectes']:
        with st.expander("🔍 Symptômes détectés"):
            for symptome in patient['symptomes_detectes']:
                points = SYMPTOME_POINTS.get(symptome, 0)
                st.write(f"- {symptome} ({points} points)")
    
    # Gestion des retards
    st.markdown("---")
    st.subheader("⏰ Gestion des retards")
    
    st.info("""
    **Règle applicable :**
    - 🔵 Retard ≤ 10 min → Consultation maintenue
    - 🔴 Retard > 10 min → Rendez-vous annulé et patient replacé en fin de file
    """)
    
    # Simulateur de retard pour démonstration
    with st.expander("📱 Simuler un retard (démonstration)"):
        retard_minutes = st.slider("Retard simulé (minutes)", 0, 60, 15)
        if st.button("Simuler l'arrivée"):
            heure_arrivee_simulee = patient['heure_rdv'] + timedelta(minutes=retard_minutes)
            resultat = gerer_retard(patient['heure_rdv'], heure_arrivee_simulee)
            
            if "annulé" in resultat:
                st.error(f"❌ {resultat}")
            else:
                st.success(f"✅ {resultat}")

# ============================================
# SECTION HISTORIQUE
# ============================================

if st.session_state.historique:
    st.markdown("---")
    st.header("📊 Historique des consultations")
    
    # Convertir en DataFrame pour affichage
    df = pd.DataFrame(st.session_state.historique)
    df_affichage = df[["nom", "service", "score", "priorite", "medecin", "heure_rdv"]].copy()
    df_affichage["heure_rdv"] = df_affichage["heure_rdv"].dt.strftime("%H:%M")
    df_affichage.columns = ["Patient", "Service", "Score", "Priorité", "Médecin", "Heure"]
    
    st.dataframe(df_affichage, use_container_width=True)

# ============================================
# PIED DE PAGE
# ============================================

st.markdown("---")
st.caption("🏥 Système Intelligent de Gestion Hospitalière - Projet étudiant")
