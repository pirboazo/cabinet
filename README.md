# Cabinet de neurologie

Application Flask locale de gestion d'un cabinet de neurologie : fiches patients, rendez-vous et comptes-rendus de consultation. Mono-utilisateur, sans authentification, prévue pour un usage local sur poste unique.

Le fonctionnement détaillé (routes, règles de validation, modèle de données) est décrit dans [SPECIFICATION.md](SPECIFICATION.md).

## Fonctionnalités

- Patients : création, fiche, modification.
- Rendez-vous : prise, modification, suppression (les comptes-rendus liés sont conservés). Deux rendez-vous non annulés ne peuvent pas se chevaucher le même jour.
- Agenda hebdomadaire : semaine du lundi au vendredi (jours ouvrés), de 8 h à 18 h, rendez-vous de 20 min à 1 h. Les rendez-vous du week-end ne sont pas affichés.
- Comptes-rendus de consultation : saisie, détail, modification, filtre par médecin.

## Stack

- Python 3.14, Flask 3.1.3, Jinja2 (gabarits dans `templates/`), SQLite (module `sqlite3`).
- CSS externe dans `static/style.css`.
- JavaScript limité à la confirmation de suppression d'un rendez-vous.

## Prérequis

- Python 3.14

## Installation

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

`requirements.txt` épingle les versions de Flask et de ses dépendances.

## Initialiser la base

```bash
venv/bin/python database/create_db.py       # crée database/cabinet.db (refuse si elle existe)
venv/bin/python database/peupler_donnees.py # optionnel : données fictives, sur base vide uniquement
```

## Mettre à jour une base existante

Une base créée avant l'ajout de la durée des rendez-vous n'a pas la colonne `duree_minutes`. L'ajouter une seule fois, depuis la racine du projet, après une sauvegarde de `database/cabinet.db` :

```bash
venv/bin/python -c "import sqlite3; c = sqlite3.connect('database/cabinet.db'); c.execute('ALTER TABLE rendez_vous ADD COLUMN duree_minutes INTEGER NOT NULL DEFAULT 30 CHECK (duree_minutes BETWEEN 20 AND 60)'); c.commit()"
```

Les rendez-vous existants reçoivent alors une durée de 30 minutes.

## Lancer l'application

```bash
venv/bin/python app.py
```

L'application écoute sur `http://127.0.0.1:5000/`. Le mode débogage est activé (`app.run(debug=True)`) : usage local uniquement, ne pas exposer sur un réseau.

## Structure

- `app.py` : routes, validation et appels aux gabarits
- `templates/base.html` : squelette commun (en-tête, menu, contenu)
- `templates/macros.html` : messages d'erreur, champs de formulaire, listes déroulantes, boutons
- `templates/patients/`, `templates/rendez_vous/`, `templates/consultations/` : une page par écran
- `static/style.css` : feuille de style
- `database/create_db.py` : création du schéma SQLite
- `database/peupler_donnees.py` : jeu de données fictif
- `database/Description.md` : description de la base

## Limites connues

Voir [SPECIFICATION.md](SPECIFICATION.md), section 7 : pas d'authentification, pas de tests automatisés versionnés.

## Licence

MIT, voir [LICENSE](LICENSE).
