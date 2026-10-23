import os
import gc
import traceback
import urllib
import pyodbc
import pandas as pd
from sqlalchemy import create_engine, text

SERVER = "localhost"
DATABASE = "DW_Smart_Energy"

connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
    f"TrustServerCertificate=yes;"
)

params = urllib.parse.quote_plus(connection_string)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

CLEAN_CSV_PATH = "data/processed/grdf_clean.csv"


def load_data_warehouse_sqlserver():
    if not os.path.exists(CLEAN_CSV_PATH):
        print(f"❌ Fichier non trouvé : {CLEAN_CSV_PATH}")
        return

    print(f"📖 Chargement du fichier nettoyé : {CLEAN_CSV_PATH}...")
    df = pd.read_csv(CLEAN_CSV_PATH, low_memory=False)

    try:
        # ----------------------------------------------------
        # 1. Alimentation de Dim_Temps
        # ----------------------------------------------------
        print("\n⏳ 1/4 Alimentation de Dim_Temps...")
        annees = df["annee"].dropna().unique()
        with engine.connect() as conn:
            for annee in annees:
                conn.execute(
                    text(
                        """
                    IF NOT EXISTS (SELECT 1 FROM Dim_Temps WHERE id_temps = :annee)
                    INSERT INTO Dim_Temps (id_temps, annee) VALUES (:annee, :annee);
                """
                    ),
                    {"annee": int(annee)},
                )
            conn.commit()
        print("   └─ Dim_Temps OK.")

        # ----------------------------------------------------
        # 2. Alimentation de Dim_Geographie
        # ----------------------------------------------------
        print("🗺️ 2/4 Alimentation de Dim_Geographie...")
        df_geo = df[
            [
                "code_iris",
                "iris",
                "code_commune",
                "commune",
                "code_epci",
                "epci",
                "code_departement",
                "departement",
                "code_region",
                "region",
            ]
        ].drop_duplicates(subset=["code_iris"])

        df_geo = df_geo.rename(
            columns={
                "iris": "libelle_iris",
                "commune": "nom_commune",
                "epci": "libelle_epci",
                "departement": "libelle_departement",
                "region": "libelle_region",
            }
        )
        df_geo = df_geo.where(pd.notnull(df_geo), None)

        existing_iris = pd.read_sql("SELECT code_iris FROM Dim_Geographie", engine)
        df_geo_new = df_geo[~df_geo["code_iris"].isin(existing_iris["code_iris"])]

        if not df_geo_new.empty:
            df_geo_new.to_sql(
                "Dim_Geographie",
                engine,
                if_exists="append",
                index=False,
                chunksize=1000,
            )
        print("   └─ Dim_Geographie OK.")

        del df_geo, df_geo_new, existing_iris
        gc.collect()

        # ----------------------------------------------------
        # 3. Alimentation de Dim_Secteur
        # ----------------------------------------------------
        print("🏢 3/4 Alimentation de Dim_Secteur...")
        naf_cols = ["code_categorie", "code_section_naf", "code_division_naf"]

        with engine.connect() as conn:
            tables = [r[0] for r in conn.execute(text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES")).fetchall()]
        
        target_sec_table = "Dim_Secteur_Activite" if "Dim_Secteur_Activite" in tables else "Dim_Secteur_Activite"

        df_sec = df[
            [
                "code_categorie",
                "secteur_activite",
                "code_section_naf",
                "section_naf",
                "code_division_naf",
                "division_naf",
            ]
        ].copy()

        for col in naf_cols:
            df_sec[col] = df_sec[col].fillna("").astype(str).str.strip()

        df_sec = df_sec.drop_duplicates(subset=naf_cols)

        df_sec_sql = df_sec.rename(
            columns={
                "secteur_activite": "libelle_grand_secteur",
                "section_naf": "libelle_section_naf",
                "division_naf": "libelle_division_naf",
            }
        ).where(pd.notnull(df_sec), None)

        existing_sec = pd.read_sql(f"SELECT COUNT(*) FROM {target_sec_table}", engine).iloc[0, 0]
        if existing_sec == 0:
            df_sec_sql.to_sql(
                target_sec_table,
                engine,
                if_exists="append",
                index=False,
                chunksize=1000,
            )
        print(f"   └─ {target_sec_table} OK.")

        del df_sec_sql
        gc.collect()

        # ----------------------------------------------------
        # 4. Chargement de Fait_Consommation_Gaz
        # ----------------------------------------------------
        print("⚡ 4/4 Alimentation de Fait_Consommation_Gaz...")

        dim_geo_db = pd.read_sql("SELECT id_geographie, code_iris FROM Dim_Geographie", engine)
        dim_geo_db = dim_geo_db.drop_duplicates(subset=["code_iris"])

        with engine.connect() as conn:
            sec_cols = [r[0] for r in conn.execute(text(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{target_sec_table}'")).fetchall()]
        sec_pk_col = "id_secteur_activite" if "id_secteur_activite" in sec_cols else "id_secteur_activite"

        dim_sec_db = pd.read_sql(
            f"SELECT {sec_pk_col}, code_categorie, code_section_naf, code_division_naf FROM {target_sec_table}",
            engine,
        )

        df["code_iris"] = df["code_iris"].astype(str).str.strip()
        dim_geo_db["code_iris"] = dim_geo_db["code_iris"].astype(str).str.strip()

        for col in naf_cols:
            df[col] = df[col].fillna("").astype(str).str.strip()
            dim_sec_db[col] = dim_sec_db[col].fillna("").astype(str).str.strip()

        # Dédoublonnage strict des dimensions BD avant la jointure pour garantir 1->1
        dim_sec_db = dim_sec_db.drop_duplicates(subset=naf_cols)

        # Jointures Pandas
        df_fait = df.merge(dim_geo_db, on="code_iris", how="left")
        df_fait = df_fait.merge(dim_sec_db, on=naf_cols, how="left")

        with engine.connect() as conn:
            fait_cols = [r[0] for r in conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Fait_Consommation_Gaz'")).fetchall()]
        fait_sec_fk = "id_secteur_activite" if "id_secteur_activite" in fait_cols else "id_secteur_activite"

        df_fait_final = pd.DataFrame(
            {
                "id_geographie": df_fait["id_geographie"],
                fait_sec_fk: df_fait[sec_pk_col],
                "id_temps": df_fait["annee"].astype(int),
                "nombre_pdl": df_fait["nombre_points_livraison"],
                "consommation_mwh": df_fait["consommation_mwh"],
                "taux_pdl_telereleves": df_fait["taux_teleleve"],
            }
        )

        records = df_fait_final.to_records(index=False)
        data_tuples = [
            (
                None if pd.isna(r[0]) else int(r[0]),
                None if pd.isna(r[1]) else int(r[1]),
                int(r[2]),
                None if pd.isna(r[3]) else int(r[3]),
                None if pd.isna(r[4]) else float(r[4]),
                None if pd.isna(r[5]) else float(r[5]),
            )
            for r in records
        ]

        raw_conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SERVER};"
            f"DATABASE={DATABASE};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
        
        insert_sql = f"""
            INSERT INTO Fait_Consommation_Gaz 
            (id_geographie, {fait_sec_fk}, id_temps, nombre_pdl, consommation_mwh, taux_pdl_telereleves)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        conn = pyodbc.connect(raw_conn_str)
        cursor = conn.cursor()
        cursor.fast_executemany = True

        # Lot réduit à 10 000 pour éviter la saturation du canal mémoire SQL Server
        batch_size = 10000
        total_rows = len(data_tuples)
        print(f"   ├─ Ingestion de {total_rows:,} lignes par paquets de {batch_size:,}...")

        for i in range(0, total_rows, batch_size):
            batch = data_tuples[i : i + batch_size]
            cursor.executemany(insert_sql, batch)
            conn.commit()
            print(f"      └─ Progrès : {min(i + batch_size, total_rows):,} / {total_rows:,} lignes")

        cursor.close()
        conn.close()

        print("   └─ Fait_Consommation_Gaz OK.")
        print(f"\n🎉 CHARGEMENT COMPLET TERMINÉ ! Lignes insérées : {total_rows:,}")

    except Exception as err:
        print("\n❌ ERREUR DÉTAILLÉE DU CHARGEMENT :")
        print("-" * 60)
        traceback.print_exc()
        print("-" * 60)


if __name__ == "__main__":
    load_data_warehouse_sqlserver()