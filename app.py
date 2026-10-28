"""Application Flask de gestion d'un cabinet de neurologie (usage local)."""

import re
import sqlite3
from contextlib import closing
from datetime import date, time, timedelta
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request

CHEMIN_BASE = Path(__file__).resolve().parent / "database" / "cabinet.db"

app = Flask(__name__)

PAGES = (
    ("/patients", "Patients"),
    ("/rendez-vous", "Rendez-vous"),
    ("/agenda", "Agenda"),
    ("/consultations", "Consultations"),
)

CHAMPS_PATIENT = (
    "nom",
    "prenom",
    "date_naissance",
    "sexe",
    "telephone",
    "email",
    "adresse",
    "antecedents",
)
SEXES = ("", "F", "M", "Autre")

CHAMPS_RDV = ("patient_id", "date_rdv", "heure_rdv", "duree_minutes", "motif", "statut")
STATUTS_RDV = ("prévu", "honoré", "annulé")
STATUT_RDV_INITIAL = "prévu"
DUREES_RDV = tuple(range(20, 61, 5))
OPTIONS_DUREE = [(str(duree), f"{duree} min") for duree in DUREES_RDV]
DUREE_RDV_INITIALE = 30
HEURE_DEBUT_AGENDA = 8
HEURE_FIN_AGENDA = 18
PIXELS_PAR_MINUTE = 2
JOURS_OUVRES = ("lundi", "mardi", "mercredi", "jeudi", "vendredi")
PATIENTS_PAR_PAGE = 12
VUES_RENDEZ_VOUS = ("tous", "jour", "semaine")

CHAMPS_CONSULTATION = (
    "patient_id",
    "rendez_vous_id",
    "date_consultation",
    "motif",
    "observations",
    "diagnostic",
    "traitement",
    "medecin",
)

OPTIONS_SEXE = [(sexe, sexe or "—") for sexe in SEXES]
OPTIONS_STATUT = [(statut, statut) for statut in STATUTS_RDV]

REGEX_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
REGEX_HEURE = re.compile(r"[0-9]{2}:[0-9]{2}")


@app.context_processor
def injecter_menu():
    return {"pages": PAGES}


# --- Base de données -------------------------------------------------------


def se_connecter_a_la_base():
    connexion = sqlite3.connect(CHEMIN_BASE)
    connexion.row_factory = sqlite3.Row
    return connexion


def patient_existe(db, patient_id):
    if patient_id is None:
        return False
    ligne = db.execute("SELECT 1 FROM patients WHERE id = ?", (patient_id,)).fetchone()
    return ligne is not None


def patients_pour_selection(db):
    return db.execute(
        """SELECT id, nom, prenom FROM patients
           ORDER BY nom COLLATE NOCASE, prenom COLLATE NOCASE, id"""
    ).fetchall()


def patients_et_rendez_vous(db):
    """Patients et rendez-vous proposés dans le formulaire de compte-rendu."""
    rendez_vous = db.execute(
        """SELECT r.id, r.date_rdv, r.heure_rdv, r.motif, p.nom, p.prenom
           FROM rendez_vous r JOIN patients p ON p.id = r.patient_id
           ORDER BY r.date_rdv DESC, r.heure_rdv DESC, r.id DESC"""
    ).fetchall()
    return patients_pour_selection(db), rendez_vous


# --- Lecture et validation des formulaires ----------------------------------


def entier_valide(valeur):
    # Limite à 18 chiffres : évite de dépasser les entiers 64 bits de SQLite.
    if not valeur.isdecimal() or len(valeur) > 18:
        return None
    return int(valeur)


def date_valide(valeur):
    if not REGEX_DATE.fullmatch(valeur):
        return False
    try:
        date.fromisoformat(valeur)
    except ValueError:
        return False
    return True


def heure_valide(valeur):
    if not REGEX_HEURE.fullmatch(valeur):
        return False
    try:
        time.fromisoformat(valeur)
    except ValueError:
        return False
    return True


def valeur_optionnelle(valeur):
    return valeur or None


def valeurs_depuis_formulaire(champs):
    return {champ: request.form.get(champ, "").strip() for champ in champs}


def valeurs_depuis_ligne(ligne, champs):
    return {champ: "" if ligne[champ] is None else str(ligne[champ]) for champ in champs}


def valeurs_depuis_formulaire_patient():
    return valeurs_depuis_formulaire(CHAMPS_PATIENT)


def erreur_formulaire_patient(valeurs):
    erreurs = []
    if not valeurs["nom"] or not valeurs["prenom"]:
        erreurs.append("Le nom et le prénom sont obligatoires.")
    if valeurs["date_naissance"] and not date_valide(valeurs["date_naissance"]):
        erreurs.append("La date de naissance n'est pas valide.")
    if valeurs["sexe"] not in SEXES:
        erreurs.append("La valeur choisie pour le sexe n'est pas valide.")
    return erreurs


def parametres_patient(valeurs):
    return tuple(valeur_optionnelle(valeurs[champ]) for champ in CHAMPS_PATIENT)


def valeurs_depuis_formulaire_rdv():
    return valeurs_depuis_formulaire(CHAMPS_RDV)


def minutes_depuis_minuit(heure):
    heures, minutes = map(int, heure.split(":"))
    return heures * 60 + minutes


def rendez_vous_chevauche(db, date_rdv, heure_rdv, duree, rdv_id):
    """Vrai si un autre rendez-vous non annulé occupe une partie du créneau."""
    debut = minutes_depuis_minuit(heure_rdv)
    fin = debut + duree
    autres = db.execute(
        """SELECT heure_rdv, duree_minutes FROM rendez_vous
           WHERE date_rdv = ? AND statut <> ? AND id IS NOT ?""",
        (date_rdv, "annulé", rdv_id),
    ).fetchall()
    return any(
        debut < minutes_depuis_minuit(autre["heure_rdv"]) + autre["duree_minutes"]
        and minutes_depuis_minuit(autre["heure_rdv"]) < fin
        for autre in autres
    )


def valider_rendez_vous(valeurs, db, rdv_id=None):
    erreurs = []
    if not patient_existe(db, entier_valide(valeurs["patient_id"])):
        erreurs.append("Merci de choisir un patient.")
    if not (date_valide(valeurs["date_rdv"]) and heure_valide(valeurs["heure_rdv"])):
        erreurs.append("Merci de saisir une date et une heure valides.")
    if valeurs["statut"] not in STATUTS_RDV:
        erreurs.append("Le statut choisi n'est pas valide.")
    if entier_valide(valeurs["duree_minutes"]) not in DUREES_RDV:
        erreurs.append("La durée choisie n'est pas valide.")
    if (
        date_valide(valeurs["date_rdv"])
        and heure_valide(valeurs["heure_rdv"])
        and entier_valide(valeurs["duree_minutes"]) in DUREES_RDV
        and valeurs["statut"] != "annulé"
        and rendez_vous_chevauche(
            db,
            valeurs["date_rdv"],
            valeurs["heure_rdv"],
            int(valeurs["duree_minutes"]),
            rdv_id,
        )
    ):
        erreurs.append("Ce créneau chevauche un autre rendez-vous.")
    return erreurs


def parametres_rendez_vous(valeurs):
    return (
        int(valeurs["patient_id"]),
        valeurs["date_rdv"],
        valeurs["heure_rdv"],
        int(valeurs["duree_minutes"]),
        valeur_optionnelle(valeurs["motif"]),
        valeurs["statut"],
    )


def valeurs_depuis_formulaire_consultation():
    return valeurs_depuis_formulaire(CHAMPS_CONSULTATION)


def valider_consultation(valeurs, db):
    erreurs = []
    patient_id = entier_valide(valeurs["patient_id"])
    if not patient_existe(db, patient_id):
        erreurs.append("Merci de choisir un patient.")

    if valeurs["rendez_vous_id"]:
        rdv_id = entier_valide(valeurs["rendez_vous_id"])
        rdv = None
        if rdv_id is not None:
            rdv = db.execute(
                "SELECT patient_id FROM rendez_vous WHERE id = ?", (rdv_id,)
            ).fetchone()
        if rdv is None:
            erreurs.append("Le rendez-vous choisi n'existe pas.")
        elif patient_id is not None and rdv["patient_id"] != patient_id:
            erreurs.append("Le rendez-vous choisi n'appartient pas à ce patient.")

    if not date_valide(valeurs["date_consultation"]):
        erreurs.append("Merci de saisir une date valide.")
    return erreurs


def parametres_consultation(valeurs):
    rdv_id = entier_valide(valeurs["rendez_vous_id"]) if valeurs["rendez_vous_id"] else None
    return (
        int(valeurs["patient_id"]),
        rdv_id,
        valeurs["date_consultation"],
        valeur_optionnelle(valeurs["motif"]),
        valeur_optionnelle(valeurs["observations"]),
        valeur_optionnelle(valeurs["diagnostic"]),
        valeur_optionnelle(valeurs["traitement"]),
        valeur_optionnelle(valeurs["medecin"]),
    )


# --- Options des listes déroulantes -----------------------------------------


def nom_complet(ligne):
    return f"{ligne['nom']} {ligne['prenom']}"


def libelle_rendez_vous(rdv):
    libelle = f"{rdv['date_rdv']} {rdv['heure_rdv']} · {nom_complet(rdv)}"
    if rdv["motif"]:
        libelle += f" · {rdv['motif']}"
    return libelle


def options_patients(patients):
    return [("", "— Choisir un patient —")] + [
        (str(p["id"]), nom_complet(p)) for p in patients
    ]


def options_rendez_vous(rendez_vous):
    return [("", "Aucun")] + [
        (str(r["id"]), libelle_rendez_vous(r)) for r in rendez_vous
    ]


# --- Rendu des formulaires --------------------------------------------------


def rendre_formulaire_patient(titre, action, valeurs, erreurs):
    return render_template(
        "patients/formulaire.html",
        titre=titre,
        action=action,
        valeurs=valeurs,
        erreurs=erreurs,
        options_sexe=OPTIONS_SEXE,
    )


def rendre_formulaire_rendez_vous(titre, action, valeurs, patients, erreurs, edition):
    return render_template(
        "rendez_vous/formulaire.html",
        titre=titre,
        action=action,
        valeurs=valeurs,
        options_patients=options_patients(patients),
        options_statut=OPTIONS_STATUT,
        options_duree=OPTIONS_DUREE,
        erreurs=erreurs,
        edition=edition,
    )


def rendre_formulaire_consultation(titre, action, valeurs, patients, rendez_vous, erreurs):
    return render_template(
        "consultations/formulaire.html",
        titre=titre,
        action=action,
        valeurs=valeurs,
        options_patients=options_patients(patients),
        options_rdv=options_rendez_vous(rendez_vous),
        erreurs=erreurs,
    )


# --- Routes : accueil et patients ------------------------------------------


@app.get("/")
def accueil():
    return redirect("/patients")


@app.get("/patients")
def liste_patients():
    with closing(se_connecter_a_la_base()) as db:
        total = db.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        nombre_pages = (total + PATIENTS_PAR_PAGE - 1) // PATIENTS_PAR_PAGE or 1
        page = min(entier_valide(request.args.get("page", "")) or 1, nombre_pages)
        patients = db.execute(
            """SELECT id, nom, prenom, date_naissance FROM patients
               ORDER BY nom COLLATE NOCASE, prenom COLLATE NOCASE, id
               LIMIT ? OFFSET ?""",
            (PATIENTS_PAR_PAGE, (page - 1) * PATIENTS_PAR_PAGE),
        ).fetchall()
    return render_template(
        "patients/liste.html",
        titre="Patients",
        patients=patients,
        page=page,
        nombre_pages=nombre_pages,
        total=total,
    )


@app.route("/patients/nouveau", methods=["GET", "POST"])
def nouveau_patient():
    if request.method == "POST":
        valeurs = valeurs_depuis_formulaire_patient()
        erreurs = erreur_formulaire_patient(valeurs)
        if not erreurs:
            with closing(se_connecter_a_la_base()) as db:
                curseur = db.execute(
                    """INSERT INTO patients
                       (nom, prenom, date_naissance, sexe, telephone, email, adresse, antecedents)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    parametres_patient(valeurs),
                )
                db.commit()
                return redirect(f"/patients/{curseur.lastrowid}")
    else:
        valeurs = {champ: "" for champ in CHAMPS_PATIENT}
        erreurs = []
    return rendre_formulaire_patient(
        "Nouveau patient", "/patients/nouveau", valeurs, erreurs
    )


@app.get("/patients/<int:patient_id>")
def fiche_patient(patient_id):
    with closing(se_connecter_a_la_base()) as db:
        patient = db.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if patient is None:
            abort(404)
        rendez_vous = db.execute(
            """SELECT r.id, r.date_rdv, r.heure_rdv, r.duree_minutes, r.motif, r.statut,
                      EXISTS (SELECT 1 FROM consultations c WHERE c.rendez_vous_id = r.id) AS a_compte_rendu
               FROM rendez_vous r
               WHERE r.patient_id = ? ORDER BY r.date_rdv, r.heure_rdv, r.id""",
            (patient_id,),
        ).fetchall()
        consultations = db.execute(
            """SELECT id, date_consultation, medecin, motif FROM consultations
               WHERE patient_id = ? ORDER BY date_consultation DESC, id DESC""",
            (patient_id,),
        ).fetchall()
    return render_template(
        "patients/fiche.html",
        titre=nom_complet(patient),
        patient=patient,
        rendez_vous=rendez_vous,
        consultations=consultations,
    )


@app.route("/patients/<int:patient_id>/modifier", methods=["GET", "POST"])
def modifier_patient(patient_id):
    with closing(se_connecter_a_la_base()) as db:
        patient = db.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if patient is None:
            abort(404)
        if request.method == "POST":
            valeurs = valeurs_depuis_formulaire_patient()
            erreurs = erreur_formulaire_patient(valeurs)
            if not erreurs:
                db.execute(
                    """UPDATE patients SET nom = ?, prenom = ?, date_naissance = ?, sexe = ?,
                       telephone = ?, email = ?, adresse = ?, antecedents = ?
                       WHERE id = ?""",
                    parametres_patient(valeurs) + (patient_id,),
                )
                db.commit()
                return redirect(f"/patients/{patient_id}")
        else:
            valeurs = valeurs_depuis_ligne(patient, CHAMPS_PATIENT)
            erreurs = []
    return rendre_formulaire_patient(
        "Modifier le patient", f"/patients/{patient_id}/modifier", valeurs, erreurs
    )


# --- Routes : rendez-vous ---------------------------------------------------


@app.get("/rendez-vous")
def liste_rendez_vous():
    vue = request.args.get("vue", "tous")
    if vue not in VUES_RENDEZ_VOUS:
        vue = "tous"
    reference = request.args.get("date", "")
    if not date_valide(reference):
        reference = date.today().isoformat()
    jour = date.fromisoformat(reference)
    if vue == "jour":
        debut, fin = jour, jour
        periode = f"Rendez-vous du {jour:%d/%m/%Y}"
    elif vue == "semaine":
        debut = jour - timedelta(days=jour.weekday())
        fin = debut + timedelta(days=6)
        periode = f"Semaine du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}"
    else:
        debut, fin = date.min, date.max
        periode = "Tous les rendez-vous"
    with closing(se_connecter_a_la_base()) as db:
        rendez_vous = db.execute(
            """SELECT r.id, r.date_rdv, r.heure_rdv, r.duree_minutes, r.motif, r.statut,
                      p.id AS patient_id, p.nom, p.prenom,
                      EXISTS (SELECT 1 FROM consultations c WHERE c.rendez_vous_id = r.id) AS a_compte_rendu
               FROM rendez_vous r JOIN patients p ON p.id = r.patient_id
               WHERE r.date_rdv BETWEEN ? AND ?
               ORDER BY r.date_rdv, r.heure_rdv, r.id""",
            (debut.isoformat(), fin.isoformat()),
        ).fetchall()
    return render_template(
        "rendez_vous/liste.html",
        titre="Rendez-vous",
        rendez_vous=rendez_vous,
        vue=vue,
        reference=reference,
        periode=periode,
    )


def lundi_de_la_semaine(valeur):
    """Renvoie le lundi de la semaine contenant la date donnée, ou celui de la semaine courante."""
    try:
        reference = date.fromisoformat(valeur)
    except ValueError:
        reference = date.today()
    return reference - timedelta(days=reference.weekday())


def position_dans_grille(heure, duree):
    """Renvoie (haut, hauteur) en pixels, ou None si le rendez-vous est hors de la plage affichée."""
    heures, minutes = map(int, heure.split(":"))
    depuis_debut = heures * 60 + minutes - HEURE_DEBUT_AGENDA * 60
    if not 0 <= depuis_debut < (HEURE_FIN_AGENDA - HEURE_DEBUT_AGENDA) * 60:
        return None
    return depuis_debut * PIXELS_PAR_MINUTE, duree * PIXELS_PAR_MINUTE


@app.get("/agenda")
def agenda():
    lundi = lundi_de_la_semaine(request.args.get("semaine", ""))
    vendredi = lundi + timedelta(days=4)
    with closing(se_connecter_a_la_base()) as db:
        rendez_vous = db.execute(
            """SELECT r.id, r.date_rdv, r.heure_rdv, r.duree_minutes, r.motif, r.statut,
                      p.id AS patient_id, p.nom, p.prenom,
                      EXISTS (SELECT 1 FROM consultations c WHERE c.rendez_vous_id = r.id) AS a_compte_rendu
               FROM rendez_vous r JOIN patients p ON p.id = r.patient_id
               WHERE r.date_rdv BETWEEN ? AND ?
               ORDER BY r.date_rdv, r.heure_rdv, r.id""",
            (lundi.isoformat(), vendredi.isoformat()),
        ).fetchall()
    colonnes = [
        {"libelle": f"{JOURS_OUVRES[i]} {lundi + timedelta(days=i):%d/%m}", "blocs": []}
        for i in range(len(JOURS_OUVRES))
    ]
    hors_plage = []
    for rdv in rendez_vous:
        position = position_dans_grille(rdv["heure_rdv"], rdv["duree_minutes"])
        if position is None:
            hors_plage.append(rdv)
        else:
            index = (date.fromisoformat(rdv["date_rdv"]) - lundi).days
            colonnes[index]["blocs"].append((rdv, *position))
    return render_template(
        "rendez_vous/agenda.html",
        titre="Agenda",
        colonnes=colonnes,
        hors_plage=hors_plage,
        lundi=lundi,
        vendredi=vendredi,
        semaine_precedente=(lundi - timedelta(days=7)).isoformat(),
        semaine_suivante=(lundi + timedelta(days=7)).isoformat(),
        heure_debut=HEURE_DEBUT_AGENDA,
        heure_fin=HEURE_FIN_AGENDA,
        hauteur_grille=(HEURE_FIN_AGENDA - HEURE_DEBUT_AGENDA) * 60 * PIXELS_PAR_MINUTE,
        hauteur_heure=60 * PIXELS_PAR_MINUTE,
    )


@app.route("/rendez-vous/nouveau", methods=["GET", "POST"])
def nouveau_rendez_vous():
    with closing(se_connecter_a_la_base()) as db:
        patients = patients_pour_selection(db)
        if request.method == "POST":
            valeurs = valeurs_depuis_formulaire_rdv()
            valeurs["statut"] = STATUT_RDV_INITIAL
            erreurs = valider_rendez_vous(valeurs, db)
            if not erreurs:
                parametres = parametres_rendez_vous(valeurs)
                db.execute(
                    """INSERT INTO rendez_vous
                       (patient_id, date_rdv, heure_rdv, duree_minutes, motif, statut)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    parametres,
                )
                db.commit()
                return redirect(f"/patients/{parametres[0]}")
        else:
            valeurs = {champ: "" for champ in CHAMPS_RDV}
            valeurs["patient_id"] = request.args.get("patient_id", "")
            valeurs["statut"] = STATUT_RDV_INITIAL
            valeurs["duree_minutes"] = str(DUREE_RDV_INITIALE)
            erreurs = []
    return rendre_formulaire_rendez_vous(
        "Nouveau rendez-vous",
        "/rendez-vous/nouveau",
        valeurs,
        patients,
        erreurs,
        edition=False,
    )


@app.route("/rendez-vous/<int:rdv_id>/modifier", methods=["GET", "POST"])
def modifier_rendez_vous(rdv_id):
    with closing(se_connecter_a_la_base()) as db:
        rdv = db.execute(
            """SELECT id, patient_id, date_rdv, heure_rdv, duree_minutes, motif, statut
               FROM rendez_vous WHERE id = ?""",
            (rdv_id,),
        ).fetchone()
        if rdv is None:
            abort(404)
        lie = db.execute(
            "SELECT EXISTS (SELECT 1 FROM consultations WHERE rendez_vous_id = ?)",
            (rdv_id,),
        ).fetchone()[0]
        if lie:
            abort(403)
        patients = patients_pour_selection(db)
        if request.method == "POST":
            valeurs = valeurs_depuis_formulaire_rdv()
            erreurs = valider_rendez_vous(valeurs, db, rdv_id)
            if not erreurs:
                db.execute(
                    """UPDATE rendez_vous SET patient_id = ?, date_rdv = ?, heure_rdv = ?,
                       duree_minutes = ?, motif = ?, statut = ? WHERE id = ?""",
                    parametres_rendez_vous(valeurs) + (rdv_id,),
                )
                db.commit()
                return redirect("/rendez-vous")
        else:
            valeurs = valeurs_depuis_ligne(rdv, CHAMPS_RDV)
            erreurs = []
    return rendre_formulaire_rendez_vous(
        "Modifier le rendez-vous",
        f"/rendez-vous/{rdv_id}/modifier",
        valeurs,
        patients,
        erreurs,
        edition=True,
    )


@app.post("/rendez-vous/<int:rdv_id>/supprimer")
def supprimer_rendez_vous(rdv_id):
    with closing(se_connecter_a_la_base()) as db:
        rdv = db.execute("SELECT id FROM rendez_vous WHERE id = ?", (rdv_id,)).fetchone()
        if rdv is None:
            abort(404)
        # Pas de PRAGMA foreign_keys : on détache les comptes-rendus à la main.
        db.execute(
            "UPDATE consultations SET rendez_vous_id = NULL WHERE rendez_vous_id = ?",
            (rdv_id,),
        )
        db.execute("DELETE FROM rendez_vous WHERE id = ?", (rdv_id,))
        db.commit()
    return redirect("/rendez-vous")


# --- Routes : comptes-rendus de consultation --------------------------------


@app.get("/consultations")
def liste_consultations():
    medecin = request.args.get("medecin", "")
    with closing(se_connecter_a_la_base()) as db:
        medecins = {
            ligne["medecin"]
            for ligne in db.execute(
                "SELECT DISTINCT medecin FROM consultations "
                "WHERE medecin IS NOT NULL AND medecin <> ''"
            )
        }
        # Un médecin filtré doit rester sélectionnable même sans résultat.
        if medecin:
            medecins.add(medecin)

        requete = (
            "SELECT c.id, c.date_consultation, c.medecin, p.nom, p.prenom "
            "FROM consultations c JOIN patients p ON p.id = c.patient_id"
        )
        parametres = ()
        if medecin:
            requete += " WHERE c.medecin = ?"
            parametres = (medecin,)
        requete += " ORDER BY c.date_consultation DESC, c.id DESC"
        consultations = db.execute(requete, parametres).fetchall()

    options_medecin = [("", "Tous les médecins")] + [
        (m, m) for m in sorted(medecins, key=str.casefold)
    ]
    return render_template(
        "consultations/liste.html",
        titre="Consultations",
        consultations=consultations,
        medecin=medecin,
        options_medecin=options_medecin,
    )


@app.route("/consultations/nouveau", methods=["GET", "POST"])
def nouveau_compte_rendu():
    with closing(se_connecter_a_la_base()) as db:
        patients, rendez_vous = patients_et_rendez_vous(db)
        if request.method == "POST":
            valeurs = valeurs_depuis_formulaire_consultation()
            erreurs = valider_consultation(valeurs, db)
            if not erreurs:
                db.execute(
                    """INSERT INTO consultations
                       (patient_id, rendez_vous_id, date_consultation, motif,
                        observations, diagnostic, traitement, medecin)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    parametres_consultation(valeurs),
                )
                db.commit()
                return redirect("/consultations")
        else:
            valeurs = {champ: "" for champ in CHAMPS_CONSULTATION}
            valeurs["patient_id"] = request.args.get("patient_id", "")
            valeurs["rendez_vous_id"] = request.args.get("rendez_vous_id", "")
            valeurs["date_consultation"] = date.today().isoformat()
            erreurs = []
    return rendre_formulaire_consultation(
        "Nouveau compte-rendu",
        "/consultations/nouveau",
        valeurs,
        patients,
        rendez_vous,
        erreurs,
    )


@app.get("/consultations/<int:consultation_id>")
def detail_consultation(consultation_id):
    with closing(se_connecter_a_la_base()) as db:
        consultation = db.execute(
            """SELECT c.*, p.nom, p.prenom, r.date_rdv, r.heure_rdv
               FROM consultations c
               JOIN patients p ON p.id = c.patient_id
               LEFT JOIN rendez_vous r ON r.id = c.rendez_vous_id
               WHERE c.id = ?""",
            (consultation_id,),
        ).fetchone()
    if consultation is None:
        abort(404)

    rdv = None
    if consultation["date_rdv"]:
        rdv = f"{consultation['date_rdv']} {consultation['heure_rdv']}"
    return render_template(
        "consultations/detail.html",
        titre="Compte-rendu de consultation",
        consultation=consultation,
        rdv=rdv,
    )


@app.route("/consultations/<int:consultation_id>/modifier", methods=["GET", "POST"])
def modifier_compte_rendu(consultation_id):
    with closing(se_connecter_a_la_base()) as db:
        consultation = db.execute(
            "SELECT * FROM consultations WHERE id = ?", (consultation_id,)
        ).fetchone()
        if consultation is None:
            abort(404)
        patients, rendez_vous = patients_et_rendez_vous(db)
        if request.method == "POST":
            valeurs = valeurs_depuis_formulaire_consultation()
            erreurs = valider_consultation(valeurs, db)
            if not erreurs:
                db.execute(
                    """UPDATE consultations SET patient_id = ?, rendez_vous_id = ?,
                       date_consultation = ?, motif = ?, observations = ?,
                       diagnostic = ?, traitement = ?, medecin = ?
                       WHERE id = ?""",
                    parametres_consultation(valeurs) + (consultation_id,),
                )
                db.commit()
                return redirect(f"/consultations/{consultation_id}")
        else:
            valeurs = valeurs_depuis_ligne(consultation, CHAMPS_CONSULTATION)
            erreurs = []
    return rendre_formulaire_consultation(
        "Modifier le compte-rendu",
        f"/consultations/{consultation_id}/modifier",
        valeurs,
        patients,
        rendez_vous,
        erreurs,
    )


if __name__ == "__main__":
    app.run(debug=True)
