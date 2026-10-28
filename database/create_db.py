"""Crée le schéma de la base du cabinet (database/cabinet.db).

Le script refuse de s'exécuter si la base existe déjà, pour ne jamais
écraser des données.
"""

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

CHEMIN_BASE = Path(__file__).resolve().parent / "cabinet.db"

SCHEMA = """
CREATE TABLE patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    date_naissance DATE,
    sexe TEXT,
    telephone TEXT,
    email TEXT,
    adresse TEXT,
    antecedents TEXT,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rendez_vous (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    date_rdv DATE NOT NULL,
    heure_rdv TIME NOT NULL,
    motif TEXT,
    statut TEXT DEFAULT 'prévu',
    duree_minutes INTEGER NOT NULL DEFAULT 30 CHECK (duree_minutes BETWEEN 20 AND 60),
    FOREIGN KEY (patient_id) REFERENCES patients (id)
);

CREATE TABLE consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    rendez_vous_id INTEGER,
    date_consultation DATE NOT NULL,
    motif TEXT,
    observations TEXT,
    diagnostic TEXT,
    traitement TEXT,
    medecin TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients (id),
    FOREIGN KEY (rendez_vous_id) REFERENCES rendez_vous (id)
);
"""


def main():
    if CHEMIN_BASE.exists():
        print(f"La base existe déjà : {CHEMIN_BASE}", file=sys.stderr)
        return 1
    with closing(sqlite3.connect(CHEMIN_BASE)) as connexion:
        connexion.executescript(SCHEMA)
        connexion.commit()
    print(f"Base créée : {CHEMIN_BASE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
