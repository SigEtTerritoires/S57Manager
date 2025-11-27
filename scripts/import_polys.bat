@echo off
setlocal enabledelayedexpansion

REM Assurez-vous qu'au moins 2 arguments ont été fournis
if "%~2"=="" (
    echo Usage: %0 directory000 output_geopackage 
    exit /b 1
)

REM Récupérer les arguments de la ligne de commande
set "directory=%~1"
set "output_geopackage=%~2"

REM Compter le nombre total de fichiers à traiter
set /a total_files=0
for /r "%directory%" %%a in (*.000) do (
    set /a total_files+=1
)

REM Initialiser le compteur de fichiers traités
set /a processed_files=0
REM Itérez sur tous les fichiers .000 dans le répertoire
for /r "%directory%" %%i in (*.000) do (
    echo Traitement du fichier: %%~ni
	set /a processed_files+=1
    echo Traitement en cours : !processed_files! sur !total_files!
	set "file=%%~ni"
    ogr2ogr -f GPKG -skipfailures -append -update -where "OGR_GEOMETRY='POLYGON' or OGR_GEOMETRY='MULTIPOLYGON'" -oo RETURN_LINKAGES=ON -oo RETURN_PRIMITIVES=ON -oo LNAM_REFS=ON -mapFieldType StringList=String,IntegerList=String "%output_geopackage%" "%%i"
    ogr2ogr -f GPKG -skipfailures -append -update "%output_geopackage%" "%%i" "DSID"
	ogr2ogr -f GPKG -skipfailures -append -update "%output_geopackage%" "%%i" "C_AGGR"
	python c:/testgpkgV2/update_geopackage_dsid_prp_prim.py "%output_geopackage%" "!file!" 
)

echo Traitement terminé.
pause
