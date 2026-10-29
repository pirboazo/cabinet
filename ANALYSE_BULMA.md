# Analyse : intégration du framework CSS Bulma

Statut : analyse seule, aucun code modifié. Les sections « Vérifié » reposent sur les sources citées ; le reste est une lecture du code actuel.

## 1. Question

Peut-on utiliser Bulma à la place (ou en complément) de la feuille `static/style.css` ?

## 2. Réponse courte

Oui. Bulma est un framework CSS pur, sans JavaScript requis pour les composants utilisés ici. Le coût principal n'est pas technique : il réside dans le renommage d'environ 70 attributs `class` répartis dans 12 gabarits, et dans la mise à jour de la spécification. L'agenda (grille positionnée en CSS) doit rester en CSS maison.

## 3. État actuel

- `static/style.css` : 39 lignes, aucune dépendance.
- `templates/base.html` : une seule feuille de style, menu en `<nav>` fait de liens `.bouton`.
- Attributs `class` dans les gabarits (grep du 2026-10-29, hors macros de champs) :

| Classe actuelle | Occurrences | Usage | Équivalent Bulma envisageable |
|---|---|---|---|
| `bouton` | 21 (dont 1 dans `nav`) | Liens et boutons d'action | `button` |
| `bouton danger` | 1 | Suppression RDV | `button is-danger` |
| `bouton actif` | 1 (menu) | Entrée de menu courante | `navbar` / `tabs` avec `is-active` |
| `actions barre` | 7 | Barres d'actions | `buttons` ou `level` |
| `actions` | 2 | Boutons de ligne | `buttons` |
| `carte` | 5 | Bloc encadré | `box` |
| `formulaire carte` | 3 | Formulaire encadré | `box` + `field` / `control` / `input` / `select` / `textarea` |
| `colonnes` | 1 | Deux colonnes fiche patient | `columns` / `column` |
| `erreurs` | 1 | Bloc d'erreurs de validation | `notification is-danger` |
| `filtre` | 1 | Formulaire de filtre médecin | `field is-grouped` |
| `vide` | 5 | Messages « Aucun … » | `has-text-grey is-italic` |
| `texte` | 5 | Texte multiligne préservé | CSS maison (`white-space: pre-wrap`) |
| `en-ligne` | 1 | Formulaire suppression inline | CSS maison |
| `pastille` | 1 | Badge « CR » de l'agenda | `tag` |
| `agenda`, `agenda-entete`, `agenda-heures`, `agenda-colonne`, `creneau` (et états `honore`, `annule`, `prevu`) | 6 | Grille horaire | **CSS maison à conserver** |

Non compté : les macros `champ()` et `select()` de `macros.html`, qui génèrent les champs de formulaire. Elles devront être revues.

Les styles de `dl` et des balises nues (`h1`, `h2`, `table`, `th`, `td`, `body`) sont aujourd'hui dans `style.css` ; leur traitement dans Bulma reste à vérifier (voir §6).

## 4. Vérifié

- Version la plus récente : **Bulma 1.0.4** (publication GitHub marquée « Latest »). Source : https://github.com/jgthms/bulma/releases
- Licence : **MIT**. Source : https://github.com/jgthms/bulma
- Distribution : archive `bulma-1.0.4.zip` sur GitHub, paquet npm `bulma`, CDN cdnjs. Source : https://bulma.io/ et https://cdnjs.com/libraries/bulma
- Le thème clair/sombre est fourni par Bulma 1.0 (`color-scheme`). Non utilisé aujourd'hui.

Non vérifié : taille du fichier `bulma.min.css` (à mesurer après téléchargement) ; liste exacte des classes disponibles dans 1.0.4 (à confirmer dans la documentation avant migration).

## 5. Options d'intégration

| Option | Principe | Avantages | Inconvénients |
|---|---|---|---|
| A. Fichier local | `static/bulma/bulma-1.0.4.min.css` copié dans le dépôt, version épinglée | Fonctionne hors ligne ; version fixe ; cohérent avec les dépendances épinglées du projet | Ajoute un fichier vendu (taille à mesurer) ; mise à jour manuelle |
| B. CDN | Balise `<link>` vers cdnjs dans `base.html` | Aucun fichier à versionner | Dépend du réseau ; version à épingler dans l'URL |
| C. Surcouche | Bulma ajouté à côté de `style.css`, classes actuelles conservées, styles maison retirés progressivement | Migration progressive, retour arrière facile | Deux systèmes de styles en parallèle pendant la transition ; risque de conflits |
| D. Migration complète | Bulma remplace les classes maison, `style.css` réduit à l'agenda | Une seule convention | Plus de modifications d'un coup ; vérification visuelle sur toutes les pages |

## 6. Points de vigilance

- **Balises nues** : Bulma applique des styles de base (typographie, marges). Les titres `h1`/`h2`, `table` et `body` du CSS actuel pourraient changer d'aspect. À vérifier par capture d'écran avant et après.
- **Collision de noms** : `bouton` et `button` coexistent sans conflit, mais un mélange dans une même page donnerait deux styles de bouton. D'où l'intérêt de migrer par page ou de tout migrer d'un bloc.
- **Agenda** : la grille repose sur `position: absolute` et des `top`/`height` en pixels calculés par Python (`position_dans_grille()`). Elle ne doit pas être touchée par Bulma. Ses styles (`agenda*`, `creneau*`) restent dans `style.css`.
- **Menu** : la règle `nav .bouton.actif` est remplacée par un composant Bulma (`navbar` ou `tabs`). Le marquage `aria-current="page"` reste à conserver.
- **Spécification** : §3.2 (couleurs `#555`, `#0066cc`, classes `.bouton`, `.danger`), §6.1 (arborescence `static/`) et §6.4 (CSS externe) décrivent le CSS actuel. Leur mise à jour exige votre accord explicite.
- **Tests** : aucune suite de tests automatisée. La vérification doit être visuelle (navigateur) sur chaque page, avec contrôle des états : menu actif, bouton danger, erreurs de formulaire, agenda, liste vide.

## 7. Plan proposé (si l'option A ou B et la migration complète sont retenues)

1. Ajouter Bulma (fichier local ou CDN) sans retirer `style.css` ; vérifier le rendu de base.
2. Migrer le menu et `base.html`.
3. Migrer `macros.html` (erreurs, boutons, champs, listes déroulantes).
4. Migrer les pages par domaine : patients, puis rendez-vous (hors agenda), puis consultations.
5. Réduire `style.css` aux seuls styles de l'agenda et aux exceptions retenues.
6. Mettre à jour `SPECIFICATION.md` (§3.2, §6.1, §6.4) et `README.md`, après autorisation.
7. Vérification visuelle sur toutes les pages, y compris l'agenda et les formulaires en erreur.

## 8. Décisions à prendre

1. Option d'intégration : A (fichier local, recommandé), B (CDN), C (surcouche) ou D (migration complète) ?
2. Périmètre : migration complète (D) ou progressive (C) ?
3. Autorisation de mettre à jour `SPECIFICATION.md` au moment de la migration ?
