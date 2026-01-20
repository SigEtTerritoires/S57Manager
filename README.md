
# 🧭 **S57Manager — Plugin QGIS pour la gestion des données ENC (S-57)**

**S57Manager** est un plugin QGIS destiné à faciliter l’import, l’affichage, la gestion et le filtrage des données ENC au format **S-57**.
Il permet notamment :

* l’import automatique des données S-57 vers une base Postgis ou GeoPackage optimisée ;
* l’affichage structuré et thématique des couches ENC ;
* le filtrage des couches par *purpose* (vue d’ensemble, générale, côtière, etc.) ;
* la gestion d’échelles d’affichage par lots ;
* divers outils ENC regroupés dans une interface unique ;
* l’accès direct au catalogue officiel NOAA ENC et l’import ciblé des cellules;
* la prise en charge du **multilingue (FR/EN/ES/PT)**.

---
## 📘 User Manual / Manuel utilisateur /Manuals del usuario / Manual do usuário

- 🇫🇷 **Français**  
  https://www.sigterritoires.fr/index.php/s57manager/

- 🇬🇧 **English**  
  https://www.sigterritoires.fr/index.php/en/s57manageren/

- 🇪🇸 **Español**  
  https://www.sigterritoires.fr/index.php/es/s57manageres/

- 🇵🇹 **Português**  
  https://www.sigterritoires.fr/index.php/pt/s57managerpt/

## 📦 **Fonctionnalités principales**


* Import de fichiers ENC (.000) vers une base GeoPackage ou une base PostGIS.
* Indexation automatique.
* Nettoyage et organisation des tables.
* Barre de progression pendant l’import.

### Organisation des tables

#### PostGIS

* Les tables sont stockées dans un schéma nommé enc
* Les noms des tables correspondent au nom S-57, préfixé par :
   * pt_ (points)
   * li_ (lignes)
   * pl_ (polygones)

#### GeoPackage

* Les tables sont stockées dans un fichier enc.gpkg
* La même convention de nommage est utilisée (pt_, li_, pl_)

### 🔹 Options S-57

* Choix du mode de stockage (GeoPackage, dossier S-57, etc.)
* Définition des chemins de données.
* Options avancées de gestion.
* Installation automatique des symboles SVG ENC.

![Options du plugin](resources/dialogsettings.png)

### Remarques importantes :

* PostGIS
   * La connexion doit être active dans QGIS
   * Il est recommandé d’utiliser une base vide
   * Le plugin modifie public.layerstyle et crée plusieurs schémas de travail
* GeoPackage
   * Il suffit d’indiquer un répertoire
   * Les fichiers nécessaires sont créés automatiquement
* Le bouton Installer les symboles SVG installe les symboles dans le profil utilisateur QGIS, et non dans le dossier SVG global

### 🔹 Import S-57

![Import des fichier .000](resources/dialogimport.png)

Le plugin parcourt le répertoire sélectionné ainsi que tous ses sous-répertoires et importe tous les fichiers .000 présents..

### 🔹 Affichage structuré des couches

* Création automatique d’un groupe QGIS dédié aux couches ENC.
* Classement par thèmes.
* Styles par défaut adaptés aux données marines.
* Activation/désactivation rapide.

![Affichage des couches](resources/dialogdisplay.png)

L’ordre de chargement est optimisé afin de garantir la visibilité de toutes les couches.

### 🔹 Outils ENC

Accessible via **Menu → S57 Manager → Outils ENC**
Fonctionnalités :

* Filtrage des couches par purpose (1 à 6).
* Suppression de tous les filtres.
* Définition d’échelles minimale et maximale pour plusieurs couches sélectionnées.
* Rafraîchissement automatique de la symbologie et du canevas.

![Outils](resources/dialogtools.png)

### Exemple d’affichage final
![Affichage des couches](resources/display2.jpg)

### Module NOAA ENC (

S57Manager intègre un module dédié au catalogue officiel NOAA ENC, permettant de rechercher et d’importer facilement des cellules ENC directement depuis QGIS.

![Accès au catalogue NOAA](resources/noaacatalog.png)

Fonctionnalités du module NOAA :
* Chargement automatique du catalogue NOAA ENC (XML officiel).
* Liste complète des cellules ENC disponibles.
* Filtrage dynamique :
   *par purpose (niveaux 1 à 6),
   *par échelle,
   *par emprise du canevas QGIS.
* Import d’une cellule NOAA sélectionnée (téléchargement + intégration S-57).
* Gestion correcte des systèmes de coordonnées :
   *emprises NOAA en EPSG:4326,
   *compatibilité avec le CRS du canevas QGIS.
* Interface intégrée au plugin (dialogue dédié).
* Support du multilingue.

### Index NOAA des ENC

Un GeoPackage d’index des cellules ENC NOAA est fourni avec S57Manager.
Chargé dans QGIS, il permet de :
* visualiser les emprises des cellules NOAA
* identifier rapidement les cartes pertinentes
* importer directement les cellules sélectionnées via le plugin

![Index du catalogue NOAA](resources/noaa_enc_index.jpg)

### 🔹 Traduction (FR/EN/ES/PT)

Le plugin charge automatiquement la traduction correspondant à la langue de QGIS :
* Français
* English
* Español
* Português

---

## 🛠️ **Installation**

### Depuis GitHub

Télécharger le dossier **S57Manager** et l’installer dans :

* **Windows**
  `C:\Users\<Utilisateur>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`

* **Linux**
  `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`

Puis relancer QGIS.

---

## 🔧 **Compilation des fichiers de traduction**

### Extraire les chaînes à traduire :

```
pylupdate5 plugin.py \
    outils_dialog.py ui_outils_dialog.py \
    gui/*.ui gui/*.py \
    logic/*.py dialogs/*.py \
    -ts i18n/S57Manager_fr.ts i18n/S57Manager_en.ts
```

### Générer les fichiers .qm :

```
lrelease i18n/S57Manager_fr.ts
lrelease i18n/S57Manager_en.ts
```

Les fichiers `.qm` sont placés dans `i18n/`.

---

## 📁 **Structure du plugin**

```
S57Manager/
 ├── plugin.py
 ├── __init__.py
 ├── logic/
 │    ├── importer.py
 │    ├── display.py
 │    ├── db_manager.py
 │    ├── settings.py
 │    └── noaa
 │         ├── catalog.py
 │         ├── downloader.py
 │         ├── importer.py
 │         ├── models.py
 │         ├── noaa_worker.py
 │         ├── updater.py
 │         └── validator.py
 ├── gui/
 │    ├── display_dialog.ui
 │    ├── import_dialog.ui
 │    ├── options_dialog.ui
 │    └── progress_dialog.py
 ├── dialogs/
 │    └── options_dialog.py
 ├── i18n/
 │    ├── S57Manager_fr.ts / .qm
 │    └── S57Manager_en.ts / .qm
 ├── outils_dialog.py
 ├── ui_outils_dialog.py
 ├── metadata.txt
 └── README.md
```

---

## 🤝 **Contributions**

Les contributions sont les bienvenues !
Merci d’ouvrir une issue ou une pull request si vous souhaitez :

* proposer une amélioration ;
* rapporter un bug ;
* ajouter de nouvelles traductions.

---

## 📜 Licence

📝 Licence **GPL v3**, comme la majorité des plugins QGIS.

---

