import urllib
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.ensemble import IsolationForest

# 1. Connexion à SQL Server
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

# 2. Extraction des séries historiques
query = """
SELECT 
    t.annee,
    g.libelle_region,
    s.libelle_grand_secteur,
    SUM(f.consommation_mwh) AS consommation_mwh,
    SUM(f.nombre_pdl) AS nombre_pdl,
    AVG(f.taux_pdl_telereleves) AS taux_telereleve
FROM Fait_Consommation_Gaz f
JOIN Dim_Temps t ON f.id_temps = t.id_temps
JOIN Dim_Geographie g ON f.id_geographie = g.id_geographie
JOIN Dim_Secteur_Activite s ON f.id_secteur_activite = s.id_secteur_activite
WHERE s.libelle_grand_secteur IS NOT NULL
GROUP BY t.annee, g.libelle_region, s.libelle_grand_secteur;
"""

print("📖 Lecture des données depuis SQL Server...")
df = pd.read_sql(query, engine)

# 3. Calcul statistique du Z-Score par (Région, Secteur)
print("⚙️ Calcul des écarts statistiques (Z-Scores)...")
group_cols = ["libelle_region", "libelle_grand_secteur"]

df["consommation_moyenne_secteur"] = df.groupby(group_cols)["consommation_mwh"].transform("mean")
df["std_secteur"] = df.groupby(group_cols)["consommation_mwh"].transform("std").fillna(1e-5)

# Calcul du Z-Score : (x - mu) / sigma
df["z_score"] = (df["consommation_mwh"] - df["consommation_moyenne_secteur"]) / df["std_secteur"]

# 4. Détection par Isolation Forest (Algorithme non supervisé)
print("🤖 Entraînement de l'Isolation Forest...")
X = df[["consommation_mwh", "nombre_pdl", "taux_telereleve", "z_score"]]

# contamination=0.05 signifie qu'on cible ~5% d'anomalies potentielles
iso_forest = IsolationForest(contamination=0.05, random_state=42)
df["score_anomalie_if"] = iso_forest.fit_predict(X)  # -1 pour anomalie, 1 pour normal

# 5. Classification des niveaux de risque
def classifier_anomalie(row):
    # Anomalie critique si rejetée par Isolation Forest ET |Z-Score| > 2
    if row["score_anomalie_if"] == -1 and abs(row["z_score"]) > 2.0:
        return "Critique"
    elif row["score_anomalie_if"] == -1 or abs(row["z_score"]) > 1.8:
        return "Modérée"
    return "Normale"

df["statut_anomalie"] = df.apply(classifier_anomalie, axis=1)

# 6. Filtrage des anomalies identifiées
anomalies = df[df["statut_anomalie"] != "Normale"].copy()

print(f"\n🚨 {len(anomalies)} anomalies détectées sur {len(df)} séries temporelles analysées.")
print(anomalies[["annee", "libelle_region", "libelle_grand_secteur", "consommation_mwh", "z_score", "statut_anomalie"]].head(10))

# 7. Sauvegarde dans SQL Server (par lots de 50 lignes pour préserver la mémoire)
cols_to_export = [
    "annee", "libelle_region", "libelle_grand_secteur", 
    "consommation_mwh", "consommation_moyenne_secteur", 
    "z_score", "score_anomalie_if", "statut_anomalie"
]

print("\n💾 Insertion des anomalies dans la table SQL Server Fait_Anomalie_Gaz...")
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE Fait_Anomalie_Gaz;"))

df[cols_to_export].to_sql(
    "Fait_Anomalie_Gaz", 
    engine, 
    if_exists="append", 
    index=False,
    chunksize=50  # Évite la saturation mémoire de SQL Server
)
print("✅ Table Fait_Anomalie_Gaz mise à jour avec succès !")