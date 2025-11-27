Installation :
1. Copier le dossier S57Manager dans le répertoire des plugins QGIS (ex: ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/)
2. Générer resources.py si nécessaire : pyrcc5 resources.qrc -o resources.py
3. Redémarrer QGIS
4. Activer le plugin via le Gestionnaire d'extensions

Dépendances externes :
- GDAL/OGR en ligne de commande (ogr2ogr, ogrinfo)
- PostgreSQL/PostGIS (si tu utilises PostGIS)

Notes :
- Le plugin utilise ogr2ogr pour importer des cellules S-57.
- Pour PostGIS, renseigner une chaîne de connexion "host=... dbname=... user=... password=... schema=..." dans les options.
