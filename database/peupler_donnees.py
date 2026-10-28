"""Remplit la base du cabinet avec un jeu de données entièrement fictif.

À exécuter une seule fois, après create_db.py, sur une base vide.
"""

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

CHEMIN_BASE = Path(__file__).resolve().parent / "cabinet.db"

# Index dans PATIENTS (0 = premier patient).
PATIENTS = [
    ("Lefèvre", "Marie", "1962-05-14", "F", "06 00 00 01 01", "marie.lefevre@example.com",
     "12 rue des Lilas, 69000 Lyon", "Migraine avec aura"),
    ("Bernard", "Thomas", "1978-11-02", "M", "06 00 00 01 02", "thomas.bernard@example.com",
     "4 allée des Tilleuls, 31000 Toulouse", None),
    ("Moreau", "Sophie", "1990-02-23", "F", "06 00 00 01 03", None,
     None, "Épilepsie généralisée, traitée"),
    ("Garnier", "Paul", "1949-08-30", "M", None, "paul.garnier@example.com",
     "18 avenue Jean Jaurès, 33000 Bordeaux", "Maladie de Parkinson (2019)"),
    ("Roux", "Élise", "2001-06-07", "F", "06 00 00 01 05", "elise.roux@example.com",
     None, None),
    ("Faure", "Antoine", "1971-01-19", "Autre", "06 00 00 01 06", "antoine.faure@example.com",
     "3 place du Marché, 44000 Nantes", "Neuropathie périphérique"),
]

# (index patient, date, heure, motif, statut)
RENDEZ_VOUS = [
    (0, "2026-10-05", "09:00", "Bilan céphalées", "honoré"),
    (0, "2026-11-09", "09:30", "Contrôle du traitement", "prévu"),
    (1, "2026-10-06", "10:15", "Tremblements des mains", "honoré"),
    (1, "2026-10-20", "14:00", "Suivi", "annulé"),
    (2, "2026-10-07", "11:00", "Crise tonico-clonique nocturne", "honoré"),
    (2, "2026-11-12", "08:45", "Bilan EEG", "prévu"),
    (3, "2026-10-08", "16:30", None, "honoré"),
    (4, "2026-11-03", "15:00", "Première consultation", "prévu"),
    (5, "2026-10-12", "09:15", "Douleurs et fourmillements des pieds", "honoré"),
]

# (index patient, index rendez-vous ou None, date, motif, observations, diagnostic, traitement, médecin)
CONSULTATIONS = [
    (0, None, "2026-09-18", "Première consultation",
     "Céphalées pulsatiles depuis six mois, souvent le matin.",
     "Suspicion de migraine avec aura", "Antalgiques de crise", "Dr Morel"),
    (0, 0, "2026-10-05", "Bilan céphalées",
     "Aura visuelle avant 4 des 6 derniers épisodes.",
     "Migraine avec aura confirmée", "Traitement de crise ; prophylaxie à réévaluer", "Dr Morel"),
    (1, 2, "2026-10-06", "Tremblements des mains",
     "Tremblement de repos discret, lenteur à la marche.",
     None, "Bilan complémentaire prescrit", "Dr Benali"),
    (2, 4, "2026-10-07", "Crise nocturne",
     "Crise tonico-clonique rapportée par l'entourage, sans morsure de langue.",
     "Épilepsie généralisée", "Introduction d'un antiépileptique", "Dr Morel"),
    (3, 6, "2026-10-08", None,
     None, None, None, "Dr Benali"),
    (5, 8, "2026-10-12", "Douleurs des pieds",
     "Paresthésies symétriques en chaussettes.",
     "Neuropathie périphérique probable", "Bilan métabolique et glycémie", None),
]


def main():
    if not CHEMIN_BASE.exists():
        print("La base n'existe pas : exécuter d'abord create_db.py.", file=sys.stderr)
        return 1
    with closing(sqlite3.connect(CHEMIN_BASE)) as connexion:
        deja_rempli = connexion.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        if deja_rempli:
            print("La base contient déjà des patients : aucune donnée ajoutée.", file=sys.stderr)
            return 1

        ids_patients = []
        for nom, prenom, naissance, sexe, telephone, email, adresse, antecedents in PATIENTS:
            curseur = connexion.execute(
                """INSERT INTO patients
                   (nom, prenom, date_naissance, sexe, telephone, email, adresse, antecedents)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (nom, prenom, naissance, sexe, telephone, email, adresse, antecedents),
            )
            ids_patients.append(curseur.lastrowid)

        ids_rdv = []
        for index, date_rdv, heure_rdv, motif, statut in RENDEZ_VOUS:
            curseur = connexion.execute(
                """INSERT INTO rendez_vous (patient_id, date_rdv, heure_rdv, motif, statut)
                   VALUES (?, ?, ?, ?, ?)""",
                (ids_patients[index], date_rdv, heure_rdv, motif, statut),
            )
            ids_rdv.append(curseur.lastrowid)

        for (index_patient, index_rdv, date, motif,
             observations, diagnostic, traitement, medecin) in CONSULTATIONS:
            rdv_id = None if index_rdv is None else ids_rdv[index_rdv]
            connexion.execute(
                """INSERT INTO consultations
                   (patient_id, rendez_vous_id, date_consultation, motif,
                    observations, diagnostic, traitement, medecin)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (ids_patients[index_patient], rdv_id, date, motif,
                 observations, diagnostic, traitement, medecin),
            )
        connexion.commit()
    print(
        f"Données fictives ajoutées : {len(PATIENTS)} patients, "
        f"{len(RENDEZ_VOUS)} rendez-vous, {len(CONSULTATIONS)} comptes-rendus."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
