from qgis.PyQt.QtSql import QSqlDatabase, QSqlQuery
from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import QSettings
from urllib.parse import quote
from qgis.core import QgsDataSourceUri
from urllib.parse import quote
class DBManager:
    def __init__(self, settings):
        self.settings = settings



    # --- Connexion PostGIS ---
    def get_connection(self):
        conninfo = self.settings.postgis_conn()
        db = QSqlDatabase.addDatabase("QPSQL", "S57Manager")
        
        for item in conninfo.split():
            if "=" not in item:
                continue
            k, v = item.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k == "host":
                db.setHostName(v)
            elif k == "dbname":
                db.setDatabaseName(v)
            elif k == "user":
                db.setUserName(v)
            elif k == "password":
                db.setPassword(v)
            elif k == "port":
                db.setPort(int(v))

        if not db.open():
            raise Exception("Impossible d’ouvrir la connexion PostGIS")
        return db

    # --- Exécuter une requête SQL ---
    def exec_sql(self, sql):
        db = self.get_connection()
        q = QSqlQuery(db)
        if not q.exec(sql):
            QgsMessageLog.logMessage(f"Erreur SQL : {q.lastError().text()}\nRequête : {sql}", "S57Manager")
            db.close()
            return False
        db.close()
        return True

    # --- Vérifier / créer schémas PostGIS ---
    def ensure_postgis_schemas(self):
        schemas = ["encm", "pointsenc", "linesenc", "polysenc", "enc"]
        for sch in schemas:
            sql = f"""
            CREATE SCHEMA IF NOT EXISTS {sch} AUTHORIZATION pg_database_owner;
            GRANT ALL ON SCHEMA {sch} TO pg_database_owner;
            """
            self.exec_sql(sql)
        QgsMessageLog.logMessage("Schémas PostGIS vérifiés et créés si nécessaire.", "S57Manager")
        # après la création des schémas
        self.setup_import_tables()
        self.setup_triggers()
        self.create_functions()
    def set_postgis_conn(self, conn_name):
        s = QSettings()
        s.setValue("S57Manager/postgis_conn", conn_name)

    def postgis_conn(self):
        s = QSettings()
        return s.value("S57Manager/postgis_conn", "")
    def setup_import_tables(self):
        """Créer les tables DSID et les séquences nécessaires dans les schémas d'import"""
        sql = """
        -- Séquences
        CREATE SEQUENCE IF NOT EXISTS pointsenc.pointsdsid_ogc_fid_seq START 1 INCREMENT 1;
        CREATE SEQUENCE IF NOT EXISTS linesenc.linesdsid_ogc_fid_seq START 1 INCREMENT 1;
        CREATE SEQUENCE IF NOT EXISTS polysenc.polysdsid_ogc_fid_seq START 1 INCREMENT 1;

        -- Tables DSID
        CREATE TABLE IF NOT EXISTS pointsenc.pointsdsid (
            ogc_fid integer NOT NULL DEFAULT nextval('pointsenc.pointsdsid_ogc_fid_seq'),
            dsid_expp numeric(3,0),
            dsid_intu numeric(3,0),
            dsid_dsnm varchar,
            dsid_edtn varchar,
            dsid_updn varchar,
            dsid_uadt varchar(8),
            dsid_isdt varchar(8),
            dsid_sted numeric(11,6),
            dsid_prsp numeric(3,0),
            dsid_psdn varchar,
            dsid_pred varchar,
            dsid_prof numeric(3,0),
            dsid_agen numeric(5,0),
            dsid_comt varchar,
            dssi_dstr numeric(3,0),
            dssi_aall numeric(3,0),
            dssi_nall numeric(3,0),
            dssi_nomr numeric(10,0),
            dssi_nocr numeric(10,0),
            dssi_nogr numeric(10,0),
            dssi_nolr numeric(10,0),
            dssi_noin numeric(10,0),
            dssi_nocn numeric(10,0),
            dssi_noed numeric(10,0),
            dssi_nofa numeric(10,0),
            dspm_hdat numeric(3,0),
            dspm_vdat numeric(3,0),
            dspm_sdat numeric(3,0),
            dspm_cscl numeric(10,0),
            dspm_duni numeric(3,0),
            dspm_huni numeric(3,0),
            dspm_puni numeric(3,0),
            dspm_coun numeric(3,0),
            dspm_comf numeric(10,0),
            dspm_somf numeric(10,0),
            dspm_comt varchar,
            CONSTRAINT pointsdsid_pkey PRIMARY KEY (ogc_fid)
        );

        CREATE TABLE IF NOT EXISTS linesenc.linesdsid ( 
            ogc_fid integer NOT NULL DEFAULT nextval('linesenc.linesdsid_ogc_fid_seq'),
            dsid_expp numeric(3,0),
            dsid_intu numeric(3,0),
            dsid_dsnm varchar,
            dsid_edtn varchar,
            dsid_updn varchar,
            dsid_uadt varchar(8),
            dsid_isdt varchar(8),
            dsid_sted numeric(11,6),
            dsid_prsp numeric(3,0),
            dsid_psdn varchar,
            dsid_pred varchar,
            dsid_prof numeric(3,0),
            dsid_agen numeric(5,0),
            dsid_comt varchar,
            dssi_dstr numeric(3,0),
            dssi_aall numeric(3,0),
            dssi_nall numeric(3,0),
            dssi_nomr numeric(10,0),
            dssi_nocr numeric(10,0),
            dssi_nogr numeric(10,0),
            dssi_nolr numeric(10,0),
            dssi_noin numeric(10,0),
            dssi_nocn numeric(10,0),
            dssi_noed numeric(10,0),
            dssi_nofa numeric(10,0),
            dspm_hdat numeric(3,0),
            dspm_vdat numeric(3,0),
            dspm_sdat numeric(3,0),
            dspm_cscl numeric(10,0),
            dspm_duni numeric(3,0),
            dspm_huni numeric(3,0),
            dspm_puni numeric(3,0),
            dspm_coun numeric(3,0),
            dspm_comf numeric(10,0),
            dspm_somf numeric(10,0),
            dspm_comt varchar,
            CONSTRAINT linesdsid_pkey PRIMARY KEY (ogc_fid)
        );
        CREATE TABLE IF NOT EXISTS polysenc.polysdsid ( 
            ogc_fid integer NOT NULL DEFAULT nextval('polysenc.polysdsid_ogc_fid_seq'),
            dsid_expp numeric(3,0),
            dsid_intu numeric(3,0),
            dsid_dsnm varchar,
            dsid_edtn varchar,
            dsid_updn varchar,
            dsid_uadt varchar(8),
            dsid_isdt varchar(8),
            dsid_sted numeric(11,6),
            dsid_prsp numeric(3,0),
            dsid_psdn varchar,
            dsid_pred varchar,
            dsid_prof numeric(3,0),
            dsid_agen numeric(5,0),
            dsid_comt varchar,
            dssi_dstr numeric(3,0),
            dssi_aall numeric(3,0),
            dssi_nall numeric(3,0),
            dssi_nomr numeric(10,0),
            dssi_nocr numeric(10,0),
            dssi_nogr numeric(10,0),
            dssi_nolr numeric(10,0),
            dssi_noin numeric(10,0),
            dssi_nocn numeric(10,0),
            dssi_noed numeric(10,0),
            dssi_nofa numeric(10,0),
            dspm_hdat numeric(3,0),
            dspm_vdat numeric(3,0),
            dspm_sdat numeric(3,0),
            dspm_cscl numeric(10,0),
            dspm_duni numeric(3,0),
            dspm_huni numeric(3,0),
            dspm_puni numeric(3,0),
            dspm_coun numeric(3,0),
            dspm_comf numeric(10,0),
            dspm_somf numeric(10,0),
            dspm_comt varchar,
            CONSTRAINT polysdsid_pkey PRIMARY KEY (ogc_fid)
        );
        """
        self.exec_sql(sql)
    def setup_triggers(self):
        """Créer les fonctions PL/pgSQL et les triggers pour DSID sur les schémas d'import"""

        sql_functions = """
        -- ======================================
        -- Fonctions pour pointsenc, linesenc, polysenc
        -- ======================================

        -- Points
        CREATE OR REPLACE FUNCTION pointsenc.create_fields_and_update()
        RETURNS TRIGGER AS $$
        DECLARE
            table_record RECORD;
            enc_chart_value TEXT;
            scale_value NUMERIC;
            purpose_value NUMERIC;
        BEGIN
            -- Récupérer les valeurs depuis pointsdsid
            SELECT dsid_dsnm, dspm_cscl, dsid_intu
            INTO enc_chart_value, scale_value, purpose_value
            FROM pointsenc.pointsdsid LIMIT 1;

            FOR table_record IN
                SELECT table_name 
                FROM information_schema.tables
                WHERE table_schema='pointsenc' 
                  AND table_name != 'pointsdsid'
            LOOP
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='pointsenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='enc_chart'
                ) THEN
                    EXECUTE format('ALTER TABLE pointsenc.%I ADD COLUMN enc_chart TEXT', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='pointsenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='scale'
                ) THEN
                    EXECUTE format('ALTER TABLE pointsenc.%I ADD COLUMN scale NUMERIC', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='pointsenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='purpose'
                ) THEN
                    EXECUTE format('ALTER TABLE pointsenc.%I ADD COLUMN purpose NUMERIC', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='pointsenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='posacc'
                ) THEN
                    EXECUTE format('ALTER TABLE pointsenc.%I ADD COLUMN posacc NUMERIC(10,0)', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='pointsenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='quapos'
                ) THEN
                    EXECUTE format('ALTER TABLE pointsenc.%I ADD COLUMN quapos INTEGER', table_record.table_name);
                END IF;

                -- Mettre à jour les valeurs depuis pointsdsid
                EXECUTE format('UPDATE pointsenc.%I SET enc_chart = $1 WHERE enc_chart IS NULL', table_record.table_name)
                USING enc_chart_value;
                EXECUTE format('UPDATE pointsenc.%I SET scale = $1 WHERE scale IS NULL', table_record.table_name)
                USING scale_value;
                EXECUTE format('UPDATE pointsenc.%I SET purpose = $1 WHERE purpose IS NULL', table_record.table_name)
                USING purpose_value;
            END LOOP;

            DELETE FROM pointsenc.pointsdsid;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;



        -- Lines
        CREATE OR REPLACE FUNCTION linesenc.create_fields_and_update()
        RETURNS TRIGGER AS $$
        DECLARE
            table_record RECORD;
            enc_chart_value TEXT;
            scale_value NUMERIC;
            purpose_value NUMERIC;
        BEGIN
            -- Récupérer les valeurs depuis linesdsid
            SELECT dsid_dsnm, dspm_cscl, dsid_intu
            INTO enc_chart_value, scale_value, purpose_value
            FROM linesenc.linesdsid LIMIT 1;

            FOR table_record IN
                SELECT table_name 
                FROM information_schema.tables
                WHERE table_schema='linesenc' 
                  AND table_name != 'linesdsid'
            LOOP
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='linesenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='enc_chart'
                ) THEN
                    EXECUTE format('ALTER TABLE linesenc.%I ADD COLUMN enc_chart TEXT', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='linesenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='scale'
                ) THEN
                    EXECUTE format('ALTER TABLE linesenc.%I ADD COLUMN scale NUMERIC', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='linesenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='purpose'
                ) THEN
                    EXECUTE format('ALTER TABLE linesenc.%I ADD COLUMN purpose NUMERIC', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='linesenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='posacc'
                ) THEN
                    EXECUTE format('ALTER TABLE linesenc.%I ADD COLUMN posacc NUMERIC(10,0)', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='linesenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='quapos'
                ) THEN
                    EXECUTE format('ALTER TABLE linesenc.%I ADD COLUMN quapos INTEGER', table_record.table_name);
                END IF;

                -- Mettre à jour les valeurs depuis linesdsid
                EXECUTE format('UPDATE linesenc.%I SET enc_chart = $1 WHERE enc_chart IS NULL', table_record.table_name)
                USING enc_chart_value;
                EXECUTE format('UPDATE linesenc.%I SET scale = $1 WHERE scale IS NULL', table_record.table_name)
                USING scale_value;
                EXECUTE format('UPDATE linesenc.%I SET purpose = $1 WHERE purpose IS NULL', table_record.table_name)
                USING purpose_value;
            END LOOP;

            DELETE FROM linesenc.linesdsid;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;



        -- Polygons
        CREATE OR REPLACE FUNCTION polysenc.create_fields_and_update()
        RETURNS TRIGGER AS $$
        DECLARE
            table_record RECORD;
            enc_chart_value TEXT;
            scale_value NUMERIC;
            purpose_value NUMERIC;
        BEGIN
            -- Récupérer les valeurs depuis polysdsid
            SELECT dsid_dsnm, dspm_cscl, dsid_intu
            INTO enc_chart_value, scale_value, purpose_value
            FROM polysenc.polysdsid LIMIT 1;

            -- Boucle sur toutes les tables du schéma sauf polysdsid
            FOR table_record IN
                SELECT table_name 
                FROM information_schema.tables
                WHERE table_schema='polysenc' 
                  AND table_name != 'polysdsid'
            LOOP
                -- Ajouter les colonnes si elles n'existent pas
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='polysenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='enc_chart'
                ) THEN
                    EXECUTE format('ALTER TABLE polysenc.%I ADD COLUMN enc_chart TEXT', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='polysenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='scale'
                ) THEN
                    EXECUTE format('ALTER TABLE polysenc.%I ADD COLUMN scale NUMERIC', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='polysenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='purpose'
                ) THEN
                    EXECUTE format('ALTER TABLE polysenc.%I ADD COLUMN purpose NUMERIC', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='polysenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='posacc'
                ) THEN
                    EXECUTE format('ALTER TABLE polysenc.%I ADD COLUMN posacc NUMERIC(10,0)', table_record.table_name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='polysenc' 
                      AND table_name=table_record.table_name 
                      AND column_name='quapos'
                ) THEN
                    EXECUTE format('ALTER TABLE polysenc.%I ADD COLUMN quapos INTEGER', table_record.table_name);
                END IF;

                -- Mettre à jour les valeurs depuis polysdsid
                EXECUTE format('UPDATE polysenc.%I SET enc_chart = $1 WHERE enc_chart IS NULL', table_record.table_name)
                USING enc_chart_value;

                EXECUTE format('UPDATE polysenc.%I SET scale = $1 WHERE scale IS NULL', table_record.table_name)
                USING scale_value;

                EXECUTE format('UPDATE polysenc.%I SET purpose = $1 WHERE purpose IS NULL', table_record.table_name)
                USING purpose_value;

            END LOOP;

            -- Supprimer les enregistrements polysdsid
            DELETE FROM polysenc.polysdsid;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;


        """

        sql_triggers = """
        -- ======================================
        -- Triggers pour chaque DSID
        -- ======================================

         -- pointsenc
        DROP TRIGGER IF EXISTS check_update_points ON pointsenc.pointsdsid;
        CREATE TRIGGER check_update_points
        AFTER INSERT ON pointsenc.pointsdsid
        FOR EACH STATEMENT
        EXECUTE FUNCTION pointsenc.create_fields_and_update();

        -- linesenc
        DROP TRIGGER IF EXISTS check_update_lines ON linesenc.linesdsid;
        CREATE TRIGGER check_update_lines
        AFTER INSERT ON linesenc.linesdsid
        FOR EACH STATEMENT
        EXECUTE FUNCTION linesenc.create_fields_and_update();

        -- polysenc
        DROP TRIGGER IF EXISTS check_update_polys ON polysenc.polysdsid;
        CREATE TRIGGER check_update_polys
        AFTER INSERT ON polysenc.polysdsid
        FOR EACH STATEMENT
        EXECUTE FUNCTION polysenc.create_fields_and_update();

        """

        # Exécution
        self.exec_sql(sql_functions)
        self.exec_sql(sql_triggers)

    def create_functions(self):
        """Ajoute les fonctions delete_all_records_in_schema et clone_tables_with_prefix dans la base"""
        db = self.get_connection()
        query = QSqlQuery(db)

        # Fonction delete_all_records_in_schema
        sql_delete_schema = """
        CREATE OR REPLACE FUNCTION public.delete_all_records_in_schema(schema_name text)
        RETURNS void
        LANGUAGE plpgsql
        AS $BODY$
        DECLARE
            table_record RECORD;
        BEGIN
            FOR table_record IN
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = schema_name AND table_type = 'BASE TABLE'
            LOOP
                EXECUTE format('DELETE FROM %I.%I', schema_name, table_record.table_name);
            END LOOP;
        END;
        $BODY$;
        """
        if not query.exec(sql_delete_schema):
            print(f"Erreur création delete_all_records_in_schema: {query.lastError().text()}")

        query.exec("ALTER FUNCTION public.delete_all_records_in_schema(text) OWNER TO postgres;")

        # Fonction clone_tables_with_prefix
        sql_clone_tables = """
        CREATE OR REPLACE FUNCTION public.clone_tables_with_prefix()
        RETURNS void AS
        $$
        DECLARE
            table_nom text;
        BEGIN
            -- PointsENC
            FOR table_nom IN (SELECT table_name FROM information_schema.tables WHERE table_schema='pointsenc' AND table_name NOT IN ('pointsdsid','isolatednode','connectednode','dsid','edge','face'))
            LOOP
                EXECUTE format('CREATE TABLE IF NOT EXISTS enc.pt_%I AS SELECT * FROM pointsenc.%I', table_nom, table_nom);
                EXECUTE format('INSERT INTO enc.pt_%I SELECT * FROM pointsenc.%I ON CONFLICT DO NOTHING', table_nom, table_nom);
                EXECUTE format('UPDATE enc.pt_%I SET posacc = isolatednode.posacc, quapos = isolatednode.quapos FROM pointsenc.isolatednode isolatednode WHERE enc.pt_%I.NAME_RCID[1] = isolatednode.RCID AND enc.pt_%I.enc_chart = isolatednode.enc_chart;', table_nom, table_nom, table_nom);
            END LOOP;

            -- LinesENC
            FOR table_nom IN (SELECT table_name FROM information_schema.tables WHERE table_schema='linesenc' AND table_name NOT IN ('linesdsid','isolatednode','connectednode','edge','dsid','face'))
            LOOP
                EXECUTE format('CREATE TABLE IF NOT EXISTS enc.li_%I AS SELECT * FROM linesenc.%I', table_nom, table_nom);
                EXECUTE format('INSERT INTO enc.li_%I SELECT * FROM linesenc.%I ON CONFLICT DO NOTHING', table_nom, table_nom);
                EXECUTE format('UPDATE enc.li_%I SET posacc = edge.posacc, quapos = edge.quapos FROM linesenc.edge edge WHERE enc.li_%I.NAME_RCID[1] = edge.RCID AND enc.li_%I.enc_chart = edge.enc_chart;', table_nom, table_nom, table_nom);
            END LOOP;

            -- PolysENC
            FOR table_nom IN (SELECT table_name FROM information_schema.tables WHERE table_schema='polysenc' AND table_name NOT IN ('polysdsid','m_qual','m_srel','dsid','edge','face','isolatednode','connectednode'))
            LOOP
                EXECUTE format('CREATE TABLE IF NOT EXISTS enc.pl_%I AS SELECT * FROM polysenc.%I', table_nom, table_nom);
                EXECUTE format('INSERT INTO enc.pl_%I SELECT * FROM polysenc.%I ON CONFLICT DO NOTHING', table_nom, table_nom);
                EXECUTE format('UPDATE enc.pl_%I SET posacc = edge.posacc, quapos = edge.quapos FROM linesenc.edge edge WHERE enc.pl_%I.NAME_RCID[1] = edge.RCID AND enc.pl_%I.enc_chart = edge.enc_chart;', table_nom, table_nom, table_nom);
            END LOOP;

            EXECUTE (SELECT public.delete_all_records_in_schema('pointsenc'));
            EXECUTE (SELECT public.delete_all_records_in_schema('linesenc'));
            EXECUTE (SELECT public.delete_all_records_in_schema('polysenc'));

            EXECUTE (SELECT update_sbdare());
        END;
        $$ LANGUAGE plpgsql;
        """
        if not query.exec(sql_clone_tables):
            print(f"Erreur création clone_tables_with_prefix: {query.lastError().text()}")
        # Fonction update_sbdare
        sql_update_sbdare = """
        CREATE OR REPLACE FUNCTION update_sbdare()
        RETURNS VOID AS
        $$
        DECLARE
            rec_row RECORD;
            natsurt VARCHAR[4];
            natquat VARCHAR[4];
            S VARCHAR[3];
            flag INT := 0;
            etiq VARCHAR(25);
            etiquet VARCHAR(25);
        BEGIN
            -- Vérifier si le champ 'label' existe, sinon le créer
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'enc'
                AND table_name = 'pt_sbdare'
                AND column_name = 'label'
            ) THEN
                EXECUTE 'ALTER TABLE enc.pt_sbdare ADD COLUMN label VARCHAR(255)';
            END IF;

            -- Parcourir les lignes avec label NULL
            FOR rec_row IN SELECT * FROM enc.pt_sbdare WHERE label IS NULL LOOP
                natsurt := ARRAY['','','',''];
                natquat := ARRAY['','','',''];
                S := ARRAY[',',',',','];
                flag := 0;

                FOR i IN 1..4 LOOP
                    IF i=4 AND flag=1 THEN
                        EXIT;
                    END IF;

                    IF rec_row.natsur[i] IS NULL THEN
                        IF flag=0 THEN
                            natsurt[i] := '0';
                        ELSE
                            natsurt[i+1] := '0';
                        END IF;

                    ELSIF strpos(rec_row.natsur[i], '/') = 0 THEN
                        IF flag=0 THEN
                            natsurt[i] := rec_row.natsur[i];
                            natquat[i] := COALESCE(rec_row.natqua[i], '0');
                        ELSE
                            natsurt[i+1] := rec_row.natsur[i];
                            natquat[i+1] := COALESCE(rec_row.natqua[i], '0');
                        END IF;

                    ELSE
                        natsurt[i] := split_part(rec_row.natsur[i], '/', 1);
                        natsurt[i+1] := split_part(rec_row.natsur[i], '/', 2);
                        natquat[i] := COALESCE(rec_row.natqua[i], '0');
                        S[i] := '/';
                        flag := 1;
                    END IF;
                END LOOP;

                etiquet := '';

                FOR i IN 1..4 LOOP
                    IF natsurt[i] <> '0' THEN
                        EXECUTE 'SELECT etiq FROM enc.natsurf WHERE NATSURT = $1 AND NATQUAT = $2'
                        INTO etiq USING natsurt[i], natquat[i];

                        IF i = 1 THEN
                            etiquet := etiq;
                        ELSE
                            etiquet := etiquet || S[i-1] || etiq;
                        END IF;
                    END IF;
                END LOOP;

                UPDATE enc.pt_sbdare
                SET label = etiquet
                WHERE pt_sbdare.ogc_fid = rec_row.ogc_fid;
            END LOOP;

        END;
        $$ LANGUAGE plpgsql;
        """

        if not query.exec(sql_update_sbdare):
            print(f"Erreur création update_sbdare: {query.lastError().text()}")
        # Activation standard conforming strings
        query.exec("SET standard_conforming_strings = ON;")

        # Suppression si la table existe
        query.exec("DROP TABLE IF EXISTS enc.natsurf CASCADE;")

        # Création de la table
        query.exec("""
        CREATE TABLE enc.natsurf (
            ogc_fid SERIAL PRIMARY KEY,
            fid NUMERIC(20,0),
            natsurt VARCHAR,
            natquat VARCHAR,
            etiq VARCHAR
        );
        """)

        # INSERT batch 1
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (1, '1', '0', 'M'), (2, '1', '1', 'fM'), (3, '1', '2', 'mM'), (4, '1', '3', 'cM'),
        (5, '1', '4', 'bkM'), (6, '1', '5', 'syM'), (7, '1', '6', 'soM'), (8, '1', '7', 'sfM'),
        (9, '1', '8', 'vM'), (10, '1', '9', 'caM'), (11, '1', '10', 'hM'), (12, '2', '0', 'Cy'),
        (13, '2', '1', 'fCy'), (14, '2', '2', 'mCy'), (15, '2', '3', 'cCy');
        """)

        # INSERT batch 2
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (16, '2', '4', 'bkCy'), (17, '2', '5', 'syCy'), (18, '2', '6', 'soCy'), (19, '2', '7', 'sfCy'),
        (20, '2', '8', 'vCy'), (21, '2', '9', 'caCy'), (22, '2', '10', 'hCy'), (23, '3', '0', 'Si'),
        (24, '3', '1', 'fSi'), (25, '3', '2', 'mSi'), (26, '3', '3', 'cSi'), (27, '3', '4', 'bkSi'),
        (28, '3', '5', 'sySi'), (29, '3', '6', 'soSi'), (30, '3', '7', 'sfSi');
        """)

        # INSERT batch 3
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (31, '3', '8', 'vSi'), (32, '3', '9', 'caSi'), (33, '3', '10', 'hSi'), (34, '4', '0', 'S'),
        (35, '4', '1', 'fS'), (36, '4', '2', 'mS'), (37, '4', '3', 'cS'), (38, '4', '4', 'bkS'),
        (39, '4', '5', 'syS'), (40, '4', '6', 'soS'), (41, '4', '7', 'sfS'), (42, '4', '8', 'vS'),
        (43, '4', '9', 'caS'), (44, '4', '10', 'hS'), (45, '5', '0', 'St');
        """)

        # INSERT batch 4
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (46, '5', '1', 'fSt'), (47, '5', '2', 'mSt'), (48, '5', '3', 'cSt'), (49, '5', '4', 'bkSt'),
        (50, '5', '5', 'sySt'), (51, '5', '6', 'soSt'), (52, '5', '7', 'sfSt'), (53, '5', '8', 'vSt'),
        (54, '5', '9', 'caSt'), (55, '5', '10', 'hSt'), (56, '6', '0', 'G'), (57, '6', '1', 'fG'),
        (58, '6', '2', 'mG'), (59, '6', '3', 'cG'), (60, '6', '4', 'bkG');
        """)

        # INSERT batch 5
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (61, '6', '5', 'syG'), (62, '6', '6', 'soG'), (63, '6', '7', 'sfG'), (64, '6', '8', 'vG'),
        (65, '6', '9', 'caG'), (66, '6', '10', 'hG'), (67, '7', '0', 'P'), (68, '7', '1', 'fP'),
        (69, '7', '2', 'mP'), (70, '7', '3', 'cP'), (71, '7', '4', 'bkP'), (72, '7', '5', 'syP'),
        (73, '7', '6', 'soP'), (74, '7', '7', 'sfP'), (75, '7', '8', 'vP');
        """)

        # INSERT batch 6
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (76, '7', '9', 'caP'), (77, '7', '10', 'hP'), (78, '8', '0', 'Cb'), (79, '8', '1', 'fCb'),
        (80, '8', '2', 'mCb'), (81, '8', '3', 'cCb'), (82, '8', '4', 'bkCb'), (83, '8', '5', 'syCb'),
        (84, '8', '6', 'soCb'), (85, '8', '7', 'sfCb'), (86, '8', '8', 'vCb'), (87, '8', '9', 'caCb'),
        (88, '8', '10', 'hCb'), (89, '9', '0', 'R'), (90, '9', '1', 'fR');
        """)

        # INSERT batch 7
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (91, '9', '2', 'mR'), (92, '9', '3', 'cR'), (93, '9', '4', 'bkR'), (94, '9', '5', 'syR'),
        (95, '9', '6', 'soR'), (96, '9', '7', 'sfR'), (97, '9', '8', 'vR'), (98, '9', '9', 'caR'),
        (99, '9', '10', 'hR'), (100, '11', '0', 'L'), (101, '11', '1', 'fL'), (102, '11', '2', 'mL'),
        (103, '11', '3', 'cL'), (104, '11', '4', 'bkL'), (105, '11', '5', 'syL');
        """)

        # INSERT batch 8
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (106, '11', '6', 'soL'), (107, '11', '7', 'sfL'), (108, '11', '8', 'vL'), (109, '11', '9', 'caL'),
        (110, '11', '10', 'hL'), (111, '14', '0', 'Co'), (112, '14', '1', 'fCo'), (113, '14', '2', 'mCo'),
        (114, '14', '3', 'cCo'), (115, '14', '4', 'bkCo'), (116, '14', '5', 'syCo'), (117, '14', '6', 'soCo'),
        (118, '14', '7', 'sfCo'), (119, '14', '8', 'vCo'), (120, '14', '9', 'caCo');
        """)

        # INSERT batch 9
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (121, '14', '10', 'hCo'), (122, '17', '0', 'Sh'), (123, '17', '1', 'fSh'), (124, '17', '2', 'mSh'),
        (125, '17', '3', 'cSh'), (126, '17', '4', 'bkSh'), (127, '17', '5', 'sySh'), (128, '17', '6', 'soSh'),
        (129, '17', '7', 'sfSh'), (130, '17', '8', 'vSh'), (131, '17', '9', 'caSh'), (132, '17', '10', 'hSh'),
        (133, '18', '0', 'Bo'), (134, '18', '1', 'fBo'), (135, '18', '2', 'mBo');
        """)

        # INSERT batch 10
        query.exec("""
        INSERT INTO enc.natsurf (fid, natsurt, natquat, etiq) VALUES
        (136, '18', '3', 'cBo'), (137, '18', '4', 'bkBo'), (138, '18', '5', 'syBo'), (139, '18', '6', 'soBo'),
        (140, '18', '7', 'sfBo'), (141, '18', '8', 'vBo'), (142, '18', '9', 'caBo'), (143, '18', '10', 'hBo');
        """)

