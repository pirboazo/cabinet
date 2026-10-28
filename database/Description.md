# Base de données du cabinet

Fichier : `database/cabinet.db` (SQLite, accès via le module `sqlite3` standard).

## Tables

- `patients` : identité et coordonnées. `nom` et `prenom` sont obligatoires ; `sexe` vaut `F`, `M`, `Autre` ou est vide.
- `rendez_vous` : rattaché à un patient (`patient_id`). `statut` vaut `prévu`, `honoré` ou `annulé`. `duree_minutes` est la durée en minutes, de 20 à 60 par pas de 5 (30 par défaut).
- `consultations` : compte-rendu rattaché à un patient, et optionnellement à un rendez-vous (`rendez_vous_id`, NULL si absent).

Les dates sont au format `AAAA-MM-JJ`, les heures au format `HH:MM`.

## Intégrité

Les clés étrangères sont déclarées dans le schéma mais SQLite ne les applique pas sans `PRAGMA foreign_keys`. L'application :

- vérifie à l'enregistrement qu'un compte-rendu lié à un rendez-vous appartient au même patient ;
- met `consultations.rendez_vous_id` à NULL avant de supprimer un rendez-vous.

## Scripts

- `create_db.py` : crée le schéma. Refuse de s'exécuter si le fichier existe.
- `peupler_donnees.py` : ajoute un jeu de données entièrement fictif. Refuse de s'exécuter si la table `patients` n'est pas vide.
