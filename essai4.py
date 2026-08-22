import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import json
from pathlib import Path

# ============================================
# CONFIGURATION DE LA PAGE
# ============================================
st.set_page_config(
    page_title="Gestion Hospitalière Intelligente",
    page_icon="🏥",
    layout="wide"
)

# ============================================
# GESTION DES MOTS DE PASSE (hashés)
# ============================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Mots de passe par défaut (à changer en production)
PASSWORDS = {
    "admin": hash_password("admin123"),
    "medecin1": hash_password("doc123"),
    "medecin2": hash_password("doc123"),
}

# ============================================
# BASE DE DONNÉES (fichier JSON)
# ============================================
DATA_FILE = "hopital_data.json"

def load_data():
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "patients": [],
        "consultations": [],
        "medecins": {
            "Dr. Martin": {"specialite": "medecine generale", "heures": [8, 16], "duree": 15, "urgences": [2,5,8,11]},
            "Dr. Diallo": {"specialite": "medecine generale", "heures": [9, 17], "duree": 15, "urgences": [3,7,10]},
            "Dr. Kone": {"specialite": "cardiologie", "heures": [8, 14], "duree": 20, "urgences": [1,4,7]},
            "Dr. Bamba": {"specialite": "pediatrie", "heures": [10, 18], "duree": 15, "urgences": [2,6,9]},
            "Dr. Touré": {"specialite": "dermatologie", "heures": [8, 12], "duree": 15, "urgences": [2,5]},
            "Dr. Kouadio": {"specialite": "gynecologie", "heures": [13, 19], "duree": 20, "urgences": [2,6,9]},
        },
        "planning": {},
        "prochain_id": 1
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

# ============================================
# INITIALISATION DES DONNÉES
# ============================================
if 'data' not in st.session_state:
    st.session_state.data = load_data()
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'page' not in st.session_state:
    st.session_state.page = "patient"  # Par défaut : page patient

# ============================================
# DICTIONNAIRES DE RÉFÉRENCE
# ============================================
SYMPTONE_TO_SERVICE = {
    "douleur thoracique": "cardiologie", "essoufflement": "cardiologie",
    "palpitations": "cardiologie", "cardiaque": "cardiologie", "poitrine": "cardiologie",
    "toux": "pneumologie", "crachat": "pneumologie", "expectoration": "pneumologie",
    "respiration": "pneumologie", "asthme": "pneumologie",
    "mal de tête": "neurologie", "migraine": "neurologie", "vertige": "neurologie",
    "perte de connaissance": "neurologie", "paralysie": "neurologie", "avc": "neurologie",
    "règle": "gynecologie", "menstruation": "gynecologie", "grossesse": "gynecologie",
    "accouchement": "gynecologie", "utérus": "gynecologie", "ovaires": "gynecologie",
    "éruption": "dermatologie", "démangeaison": "dermatologie", "bouton": "dermatologie",
    "peau": "dermatologie", "plaque": "dermatologie",
    "ventre": "gastro-enterologie", "estomac": "gastro-enterologie", "nausée": "gastro-enterologie",
    "vomissement": "gastro-enterologie", "diarrhée": "gastro-enterologie", "constipation": "gastro-enterologie",
    "urine": "urologie", "rénal": "urologie", "rein": "urologie", "vessie": "urologie",
    "œil": "ophtalmologie", "vue": "ophtalmologie", "vision": "ophtalmologie",
    "oreille": "orl", "nez": "orl", "gorge": "orl", "audition": "orl",
}

SYMPTOME_POINTS = {
    "douleur thoracique": 4, "essoufflement": 3, "perte de connaissance": 5,
    "paralysie": 5, "avc": 5, "hémorragie": 5, "fracture": 4, "fièvre": 3,
    "vomissement": 2, "diarrhée": 2, "démangeaison": 1, "éruption": 1,
    "toux": 1, "mal de tête": 2, "vertige": 2, "palpitations": 3,
}

RED_FLAGS = ["douleur thoracique", "perte de connaissance", "paralysie", "avc", "hémorragie"]

# ============================================
# FONCTIONS DE TRAITEMENT
# ============================================
def analyser_symptomes(texte):
    texte_lower = texte.lower()
    symptomes_detectes = []
    score = 0
    
    for symptome, points in SYMPTOME_POINTS.items():
        if symptome in texte_lower:
            symptomes_detectes.append(symptome)
            score += points
    
    service_score = {}
    for symptome in symptomes_detectes:
        for mot_cle, service in SYMPTONE_TO_SERVICE.items():
            if symptome == mot_cle or mot_cle in symptome:
                if service not in service_score:
                    service_score[service] = 0
                service_score[service] += SYMPTOME_POINTS.get(symptome, 1)
    
    service_deduit = max(service_score, key=service_score.get) if service_score else "medecine generale"
    
    if score <= 3:
        priorite = "Faible"
    elif score <= 7:
        priorite = "Moyenne"
    elif score <= 12:
        priorite = "Élevée"
    else:
        priorite = "URGENCE"
    
    return service_deduit, score, priorite, symptomes_detectes

def trouver_medecin_disponible(service, data, est_urgent=False):
    medecins_disponibles = []
    for nom, infos in data["medecins"].items():
        if infos["specialite"] == service or infos["specialite"] == "medecine generale":
            medecins_disponibles.append(nom)
    
    if not medecins_disponibles:
        return None
    
    if est_urgent:
        for nom in medecins_disponibles:
            if nom not in data["planning"] or len(data["planning"][nom]) < 10:
                return nom
    
    charge_min = float('inf')
    medecin_choisi = medecins_disponibles[0]
    for nom in medecins_disponibles:
        charge = len(data["planning"].get(nom, {}))
        if charge < charge_min:
            charge_min = charge
            medecin_choisi = nom
    
    return medecin_choisi

def attribuer_heure(medecin_nom, data, est_urgent=False):
    infos = data["medecins"][medecin_nom]
    heure_debut, heure_fin = infos["heures"]
    duree = infos["duree"]
    planning = data["planning"].get(medecin_nom, {})
    creneaux_urgence = infos["urgences"]
    
    creneaux = []
    heure_courante = datetime.now().replace(hour=heure_debut, minute=0, second=0, microsecond=0)
    heure_fin_datetime = datetime.now().replace(hour=heure_fin, minute=0, second=0, microsecond=0)
    
    index = 0
    while heure_courante < heure_fin_datetime:
        if est_urgent and index in creneaux_urgence:
            creneaux.append(heure_courante)
        elif not est_urgent and index not in creneaux_urgence:
            creneaux.append(heure_courante)
        heure_courante += timedelta(minutes=duree)
        index += 1
    
    # Convertir les heures existantes en datetime pour comparaison
    creneaux_occupes = []
    for cle, val in planning.items():
        if isinstance(val, str):
            try:
                creneaux_occupes.append(datetime.fromisoformat(val))
            except:
                pass
        elif isinstance(val, datetime):
            creneaux_occupes.append(val)
    
    creneaux_disponibles = [c for c in creneaux if c not in creneaux_occupes]
    
    if not creneaux_disponibles:
        return None
    
    heure_rdv = creneaux_disponibles[0]
    
    if medecin_nom not in data["planning"]:
        data["planning"][medecin_nom] = {}
    
    data["planning"][medecin_nom][str(len(data["planning"][medecin_nom]))] = heure_rdv.isoformat()
    
    return heure_rdv

def calculer_nouvelle_heure_retard(patient, data):
    """Calcule une nouvelle heure en plaçant le patient en fin de file"""
    # Trouver le dernier patient enregistré
    heure_max = None
    
    for p in data["patients"]:
        if p.get("medecin") == patient["medecin"] and p.get("id") != patient["id"]:
            if p.get("heure_rdv"):
                try:
                    h = datetime.fromisoformat(p["heure_rdv"])
                    if heure_max is None or h > heure_max:
                        heure_max = h
                except:
                    pass
    
    if heure_max is None:
        # Aucun autre patient, prendre l'heure actuelle + 15 min
        nouvelle_heure = datetime.now() + timedelta(minutes=15)
    else:
        # Ajouter la durée de consultation après le dernier patient
        infos = data["medecins"].get(patient["medecin"], {})
        duree = infos.get("duree", 15)
        nouvelle_heure = heure_max + timedelta(minutes=duree)
    
    return nouvelle_heure

def gerer_retard(patient, data):
    """Gère le retard en recalculant l'heure"""
    nouvelle_heure = calculer_nouvelle_heure_retard(patient, data)
    
    # Mettre à jour l'heure du patient
    for p in data["patients"]:
        if p.get("id") == patient["id"]:
            p["heure_rdv"] = nouvelle_heure.isoformat()
            p["retard_ge"] = True
            p["nouvelle_heure"] = nouvelle_heure.isoformat()
            break
    
    # Mettre à jour le planning du médecin
    medecin = patient["medecin"]
    if medecin in data["planning"]:
        # Retirer l'ancien créneau
        for cle, val in list(data["planning"][medecin].items()):
            if isinstance(val, str) and patient["heure_rdv_original"] in val:
                del data["planning"][medecin][cle]
                break
        # Ajouter le nouveau créneau
        data["planning"][medecin][str(len(data["planning"][medecin]))] = nouvelle_heure.isoformat()
    
    save_data(data)
    return nouvelle_heure

# ============================================
# PAGE PATIENT (ACCÈS LIBRE - SANS CODE)
# ============================================
def page_patient():
    st.title("🏥 Prise de rendez-vous en ligne")
    st.markdown("---")
    st.caption("📋 Remplissez le formulaire ci-dessous pour prendre un rendez-vous. Le système analysera vos symptômes et vous attribuera automatiquement une heure de consultation.")
    st.markdown("---")
    
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
        
        submitted = st.form_submit_button("📤 Envoyer ma demande", use_container_width=True)
        
        if submitted:
            if not nom or not age or not telephone or not symptomes:
                st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
            else:
                # Analyse des symptômes
                service, score, priorite, symptomes_detectes = analyser_symptomes(symptomes)
                est_urgent = priorite == "URGENCE"
                red_flag_detecte = any(flag in symptomes.lower() for flag in RED_FLAGS)
                
                if red_flag_detecte or est_urgent:
                    st.warning("🚨 **URGENCE DÉTECTÉE !** Rendez-vous immédiatement aux urgences.")
                    st.info(f"📋 Symptômes détectés : {', '.join(symptomes_detectes) if symptomes_detectes else 'Aucun'}")
                    st.stop()
                
                # Trouver un médecin disponible
                medecin = trouver_medecin_disponible(service, st.session_state.data, est_urgent)
                
                if not medecin:
                    st.error("❌ Aucun médecin disponible pour ce service. Veuillez réessayer plus tard.")
                    st.stop()
                
                # Attribuer une heure
                heure_rdv = attribuer_heure(medecin, st.session_state.data, est_urgent)
                
                if not heure_rdv:
                    st.error("❌ Aucun créneau disponible. Veuillez réessayer plus tard.")
                    st.stop()
                
                # Enregistrer le patient
                patient_id = st.session_state.data["prochain_id"]
                st.session_state.data["prochain_id"] += 1
                
                patient = {
                    "id": patient_id,
                    "nom": nom,
                    "age": age,
                    "sexe": sexe,
                    "telephone": telephone,
                    "email": email,
                    "symptomes": symptomes,
                    "symptomes_detectes": symptomes_detectes,
                    "service": service,
                    "score": score,
                    "priorite": priorite,
                    "medecin": medecin,
                    "heure_rdv": heure_rdv.isoformat(),
                    "heure_rdv_original": heure_rdv.isoformat(),
                    "est_urgent": est_urgent,
                    "retard_ge": False,
                    "date_inscription": datetime.now().isoformat()
                }
                
                st.session_state.data["patients"].append(patient)
                save_data(st.session_state.data)
                
                st.success("✅ Votre rendez-vous a été confirmé avec succès !")
                
                # Affichage pour le patient (sans score ni priorité)
                st.markdown("---")
                st.subheader("📋 Récapitulatif de votre rendez-vous")
                
                heure_formatee = heure_rdv.strftime("%H:%M")
                heure_arrivee = (heure_rdv - timedelta(minutes=10)).strftime("%H:%M")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**👤 Patient:** {nom}")
                    st.write(f"**📞 Téléphone:** {telephone}")
                with col2:
                    st.write(f"**📅 Date:** {heure_rdv.strftime('%d/%m/%Y')}")
                    st.write(f"**🕐 Heure:** {heure_formatee}")
                
                st.success(f"""
                ### 🕐 Votre consultation est prévue à **{heure_formatee}**
                
                ⚠️ **Arrivez à {heure_arrivee}** (10 minutes avant)
                
                📍 **Service:** {service.upper()}
                👨‍⚕️ **Médecin:** {medecin}
                """)
                
                # Gestion des retards
                st.markdown("---")
                st.subheader("⏰ En cas de retard")
                st.info("""
                **Règle :**
                - Retard ≤ 10 min → Consultation maintenue à l'heure prévue
                - Retard > 10 min → Nouvelle heure calculée automatiquement en fin de file
                """)
                
                # Simulateur de retard
                with st.expander("📱 Simuler un retard (démonstration)"):
                    retard_minutes = st.slider("Retard (minutes)", 0, 60, 15)
                    if st.button("Simuler l'arrivée"):
                        if retard_minutes > 10:
                            # Recalculer l'heure
                            nouvelle_heure = gerer_retard(patient, st.session_state.data)
                            st.warning(f"⚠️ Retard de {retard_minutes} minutes détecté.")
                            st.success(f"🕐 Nouvelle heure de passage : {nouvelle_heure.strftime('%H:%M')}")
                            st.info(f"📌 Vous serez reçu après le dernier patient enregistré.")
                        else:
                            st.success(f"✅ Retard de {retard_minutes} minutes. Consultation maintenue à l'heure prévue.")

# ============================================
# PAGE DE CONNEXION (Médecins et Admin)
# ============================================
def login_page():
    st.title("🔐 Espace réservé")
    st.markdown("---")
    st.caption("Cette section est réservée aux médecins et à l'administration.")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        role = st.selectbox("Rôle", ["Médecin", "Administrateur"])
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        
        if st.button("Se connecter", use_container_width=True):
            if role == "Médecin":
                if username in ["Dr. Martin", "Dr. Diallo", "Dr. Kone", "Dr. Bamba", "Dr. Touré", "Dr. Kouadio"]:
                    # Vérification du mot de passe
                    medecin_key = None
                    for key, val in PASSWORDS.items():
                        if key.startswith("medecin") and hash_password(password) == val:
                            medecin_key = key
                            break
                    
                    if medecin_key:
                        st.session_state.logged_in = True
                        st.session_state.role = "medecin"
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("❌ Mot de passe incorrect")
                else:
                    st.error("❌ Médecin non reconnu")
            elif role == "Administrateur":
                if username == "admin" and hash_password(password) == PASSWORDS["admin"]:
                    st.session_state.logged_in = True
                    st.session_state.role = "admin"
                    st.session_state.username = "admin"
                    st.rerun()
                else:
                    st.error("❌ Identifiants incorrects")

# ============================================
# PAGE MÉDECIN
# ============================================
def page_medecin():
    st.title(f"👨‍⚕️ Espace Médecin - {st.session_state.username}")
    st.markdown("---")
    
    # Récupérer les patients du médecin
    patients_medecin = [p for p in st.session_state.data["patients"] if p.get("medecin") == st.session_state.username]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Patients aujourd'hui", len(patients_medecin))
    with col2:
        en_attente = len([p for p in patients_medecin if p.get("retard_ge", False)])
        st.metric("⏰ En retard", en_attente)
    with col3:
        urgences = len([p for p in patients_medecin if p.get("priorite") == "URGENCE"])
        st.metric("🚨 Urgences", urgences)
    
    st.markdown("---")
    
    if patients_medecin:
        st.subheader("📋 Liste des patients")
        
        # Préparer les données
        df = pd.DataFrame(patients_medecin)
        df = df.sort_values("heure_rdv")
        
        df_affichage = df[[
            "id", "nom", "age", "telephone", "service", 
            "score", "priorite", "heure_rdv", "symptomes"
        ]].copy()
        
        df_affichage["heure_rdv"] = pd.to_datetime(df_affichage["heure_rdv"]).dt.strftime("%H:%M")
        df_affichage.columns = ["ID", "Patient", "Âge", "Téléphone", "Service", "Score", "Priorité", "Heure", "Symptômes"]
        
        # Colorier selon la priorité
        def color_priorite(val):
            if val == "URGENCE":
                return "background-color: #ff4444; color: white"
            elif val == "Élevée":
                return "background-color: #ff8800; color: white"
            elif val == "Moyenne":
                return "background-color: #ffcc00"
            else:
                return ""
        
        st.dataframe(
            df_affichage.style.applymap(color_priorite, subset=["Priorité"]),
            use_container_width=True,
            hide_index=True
        )
        
        # Détails d'un patient
        st.markdown("---")
        st.subheader("🔍 Détails d'un patient")
        
        patient_selectionne = st.selectbox(
            "Sélectionner un patient",
            options=[f"{p['id']} - {p['nom']}" for p in patients_medecin]
        )
        
        if patient_selectionne:
            patient_id = int(patient_selectionne.split(" - ")[0])
            patient = next(p for p in patients_medecin if p["id"] == patient_id)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Nom:** {patient['nom']}")
                st.write(f"**Âge:** {patient['age']} ans")
                st.write(f"**Sexe:** {patient['sexe']}")
                st.write(f"**Téléphone:** {patient['telephone']}")
                st.write(f"**Email:** {patient.get('email', 'Non renseigné')}")
            with col2:
                st.write(f"**Service:** {patient['service'].upper()}")
                st.write(f"**Score clinique:** {patient['score']}/12")
                st.write(f"**Priorité:** {patient['priorite']}")
                heure = datetime.fromisoformat(patient['heure_rdv']).strftime("%H:%M")
                st.write(f"**Heure prévue:** {heure}")
                if patient.get('retard_ge', False):
                    nouvelle_heure = datetime.fromisoformat(patient['nouvelle_heure']).strftime("%H:%M")
                    st.warning(f"⚠️ Patient en retard - Nouvelle heure: {nouvelle_heure}")
            
            st.write("**Symptômes:**", patient['symptomes'])
            if patient.get('symptomes_detectes'):
                st.write("**Symptômes détectés:**", ", ".join(patient['symptomes_detectes']))
    else:
        st.info("📭 Aucun patient pour le moment")

# ============================================
# PAGE ADMINISTRATEUR
# ============================================
def page_admin():
    st.title("🏥 Administration - Tableau de bord")
    st.markdown("---")
    
    data = st.session_state.data
    
    # Statistiques générales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total patients", len(data["patients"]))
    with col2:
        st.metric("👨‍⚕️ Médecins", len(data["medecins"]))
    with col3:
        rdv_aujourdhui = len([p for p in data["patients"] if datetime.fromisoformat(p["heure_rdv"]).date() == datetime.now().date()])
        st.metric("📅 Rendez-vous aujourd'hui", rdv_aujourdhui)
    with col4:
        urgences = len([p for p in data["patients"] if p.get("priorite") == "URGENCE"])
        st.metric("🚨 Urgences détectées", urgences)
    
    st.markdown("---")
    
    # Graphiques et stats
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Répartition par service")
        services = [p.get("service", "Non défini") for p in data["patients"]]
        if services:
            df_services = pd.DataFrame(services, columns=["Service"])
            st.bar_chart(df_services["Service"].value_counts())
        else:
            st.info("Aucune donnée disponible")
    
    with col2:
        st.subheader("📊 Répartition des priorités")
        priorites = [p.get("priorite", "Non défini") for p in data["patients"]]
        if priorites:
            df_priorites = pd.DataFrame(priorites, columns=["Priorité"])
            st.bar_chart(df_priorites["Priorité"].value_counts())
        else:
            st.info("Aucune donnée disponible")
    
    st.markdown("---")
    
    # Liste de tous les patients
    st.subheader("📋 Tous les patients")
    
    if data["patients"]:
        df = pd.DataFrame(data["patients"])
        df = df.sort_values("date_inscription", ascending=False)
        
        df_affichage = df[[
            "id", "nom", "age", "telephone", "service", 
            "score", "priorite", "medecin", "heure_rdv"
        ]].copy()
        
        df_affichage["heure_rdv"] = pd.to_datetime(df_affichage["heure_rdv"]).dt.strftime("%H:%M")
        df_affichage.columns = ["ID", "Patient", "Âge", "Téléphone", "Service", "Score", "Priorité", "Médecin", "Heure"]
        
        # Colorier selon la priorité
        def color_priorite(val):
            if val == "URGENCE":
                return "background-color: #ff4444; color: white"
            elif val == "Élevée":
                return "background-color: #ff8800; color: white"
            elif val == "Moyenne":
                return "background-color: #ffcc00"
            else:
                return ""
        
        st.dataframe(
            df_affichage.style.applymap(color_priorite, subset=["Priorité"]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Aucun patient enregistré")
    
    st.markdown("---")
    
    # Gestion des médecins
    st.subheader("👨‍⚕️ Gestion des médecins")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Médecins disponibles:**")
        for nom, infos in data["medecins"].items():
            nb_patients = len([p for p in data["patients"] if p.get("medecin") == nom])
            st.write(f"- {nom} ({infos['specialite']}) - {nb_patients} patients")
    
    with col2:
        st.write("**Charges par médecin:**")
        charges = {}
        for nom in data["medecins"].keys():
            charges[nom] = len([p for p in data["patients"] if p.get("medecin") == nom])
        
        if charges:
            df_charges = pd.DataFrame(list(charges.items()), columns=["Médecin", "Patients"])
            st.bar_chart(df_charges.set_index("Médecin"))
    
    st.markdown("---")
    
    # Export des données
    with st.expander("📥 Export des données"):
        if data["patients"]:
            df_export = pd.DataFrame(data["patients"])
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📊 Télécharger CSV",
                data=csv,
                file_name=f"export_hopital_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    # Réinitialiser les données
    with st.expander("⚠️ Administration avancée"):
        if st.button("🗑️ Réinitialiser toutes les données", type="secondary"):
            if st.checkbox("☑️ Confirmer la réinitialisation"):
                st.session_state.data = {
                    "patients": [],
                    "consultations": [],
                    "medecins": data["medecins"],
                    "planning": {},
                    "prochain_id": 1
                }
                save_data(st.session_state.data)
                st.success("✅ Données réinitialisées avec succès")
                st.rerun()

# ============================================
# BARRE DE NAVIGATION
# ============================================
st.sidebar.title("🏥 Navigation")

# Le patient accède directement à l'inscription sans connexion
if st.sidebar.button("📝 Prise de rendez-vous", use_container_width=True):
    st.session_state.page = "patient"
    if st.session_state.logged_in:
        # Déconnecter si un médecin/admin était connecté
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = None
    st.rerun()

st.sidebar.markdown("---")

# Espace réservé (Médecins et Admin)
st.sidebar.subheader("🔐 Espace réservé")

if not st.session_state.logged_in:
    if st.sidebar.button("👨‍⚕️ Médecins / Admin", use_container_width=True):
        st.session_state.page = "login"
        st.rerun()
else:
    # Afficher le rôle connecté
    if st.session_state.role == "medecin":
        st.sidebar.success(f"👨‍⚕️ {st.session_state.username}")
    elif st.session_state.role == "admin":
        st.sidebar.success(f"👑 Administrateur")
    
    if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = None
        st.session_state.page = "patient"
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("© Gestion Hospitalière Intelligente")

# ============================================
# ROUTAGE PRINCIPAL
# ============================================
if st.session_state.page == "patient":
    page_patient()
elif st.session_state.page == "login" and not st.session_state.logged_in:
    login_page()
elif st.session_state.logged_in and st.session_state.role == "medecin":
    page_medecin()
elif st.session_state.logged_in and st.session_state.role == "admin":
    page_admin()
else:
    page_patient()  # Par défaut : page patient
