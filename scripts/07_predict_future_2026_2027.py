import urllib
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.ensemble import RandomForestRegressor

# 1. Connexion à la base de données
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

# 2. Extraction des données historiques agrégées (2018-2025)
query = """
SELECT 
    t.annee,
    g.libelle_region,
    s.libelle_grand_secteur,
    SUM(f.consommation_mwh) AS consommation_mwh
FROM Fait_Consommation_Gaz f
JOIN Dim_Temps t ON f.id_temps = t.id_temps
JOIN Dim_Geographie g ON f.id_geographie = g.id_geographie
JOIN Dim_Secteur_Activite s ON f.id_secteur_activite = s.id_secteur_activite
WHERE s.libelle_grand_secteur IS NOT NULL
GROUP BY t.annee, g.libelle_region, s.libelle_grand_secteur
ORDER BY g.libelle_region, s.libelle_grand_secteur, t.annee;
"""

print("📖 Chargement des données historiques...")
df_hist = pd.read_sql(query, engine)

# 3. Préparation des Lags pour l'entraînement
df_sorted = df_hist.sort_values(["libelle_region", "libelle_grand_secteur", "annee"]).copy()
df_sorted["lag_consommation_n1"] = df_sorted.groupby(["libelle_region", "libelle_grand_secteur"])["consommation_mwh"].shift(1)
df_sorted["lag_consommation_n2"] = df_sorted.groupby(["libelle_region", "libelle_grand_secteur"])["consommation_mwh"].shift(2)

df_train = df_sorted.dropna().copy()

# One-Hot Encoding
df_encoded = pd.get_dummies(df_train, columns=["libelle_region", "libelle_grand_secteur"], drop_first=False)
feature_cols = [c for c in df_encoded.columns if c not in ["annee", "consommation_mwh"]]

X_train = df_encoded[feature_cols]
y_train = df_encoded["consommation_mwh"]

# 4. Entraînement sur tout l'historique
print("🤖 Entraînement du modèle sur tout l'historique (2018-2025)...")
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 5. Projection pour 2026
print("🔮 Calcul des projections pour 2026...")
last_pair = df_hist[df_hist["annee"].isin([2024, 2025])].pivot(
    index=["libelle_region", "libelle_grand_secteur"], 
    columns="annee", 
    values="consommation_mwh"
).reset_index()

last_pair.columns.name = None
last_pair = last_pair.rename(columns={2024: "lag_consommation_n2", 2025: "lag_consommation_n1"})
last_pair["annee"] = 2026

# Encodage pour 2026
X_2026 = pd.get_dummies(last_pair, columns=["libelle_region", "libelle_grand_secteur"], drop_first=False)
# Alignement exact des colonnes
for col in feature_cols:
    if col not in X_2026.columns:
        X_2026[col] = 0

X_2026 = X_2026[feature_cols]
pred_2026_mwh = model.predict(X_2026)

df_2026 = last_pair[["libelle_region", "libelle_grand_secteur"]].copy()
df_2026["annee"] = 2026
df_2026["consommation_mwh"] = pred_2026_mwh
df_2026["lag_consommation_n1"] = pred_2026_mwh
df_2026["lag_consommation_n2"] = last_pair["lag_consommation_n1"].values

# 6. Projection pour 2027
print("🔮 Calcul des projections pour 2027...")
X_2027 = pd.get_dummies(df_2026, columns=["libelle_region", "libelle_grand_secteur"], drop_first=False)
for col in feature_cols:
    if col not in X_2027.columns:
        X_2027[col] = 0

X_2027 = X_2027[feature_cols]
pred_2027_mwh = model.predict(X_2027)

df_2027 = df_2026[["libelle_region", "libelle_grand_secteur"]].copy()
df_2027["annee"] = 2027
df_2027["consommation_mwh"] = pred_2027_mwh

# 7. Assemblage final Réel vs Projections
df_hist_export = df_hist[["annee", "libelle_region", "libelle_grand_secteur", "consommation_mwh"]].copy()
df_hist_export["type_donnee"] = "Réel"

df_2026_export = df_2026[["annee", "libelle_region", "libelle_grand_secteur", "consommation_mwh"]].copy()
df_2026_export["type_donnee"] = "Projection ML"

df_2027_export = df_2027[["annee", "libelle_region", "libelle_grand_secteur", "consommation_mwh"]].copy()
df_2027_export["type_donnee"] = "Projection ML"

df_final = pd.concat([df_hist_export, df_2026_export, df_2027_export], ignore_index=True)

# 8. Écriture dans SQL Server
print("💾 Insertion des résultats dans SQL Server (table Fait_Prediction_Gaz)...")
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE Fait_Prediction_Gaz;"))

df_final.to_sql("Fait_Prediction_Gaz", engine, if_exists="append", index=False)
print("✅ Projections 2026 et 2027 insérées avec succès dans SQL Server !")