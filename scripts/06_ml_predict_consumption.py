import urllib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy import create_engine

# ----------------------------------------------------
# 1. Connexion à SQL Server et Extraction
# ----------------------------------------------------
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
GROUP BY t.annee, g.libelle_region, s.libelle_grand_secteur
ORDER BY g.libelle_region, s.libelle_grand_secteur, t.annee;
"""

print("📖 Extraction des données agrégées depuis SQL Server...")
df = pd.read_sql(query, engine)
print(f"   └─ {len(df)} séries temporelles extraites.")

# ----------------------------------------------------
# 2. Feature Engineering (Lags Temporels)
# ----------------------------------------------------
print("\n⚙️ Génération des variables prédictives (Feature Engineering)...")

# Tri strict pour le calcul des lags
df = df.sort_values(["libelle_region", "libelle_grand_secteur", "annee"])

# Création du Lag N-1 (consommation de l'année précédente)
df["lag_consommation_n1"] = df.groupby(
    ["libelle_region", "libelle_grand_secteur"]
)["consommation_mwh"].shift(1)

# Création du Lag N-2
df["lag_consommation_n2"] = df.groupby(
    ["libelle_region", "libelle_grand_secteur"]
)["consommation_mwh"].shift(2)

# Suppression des lignes avec des Lags manquants (premières années)
df_ml = df.dropna().copy()

# Encodage One-Hot des variables catégorielles
df_ml_encoded = pd.get_dummies(
    df_ml,
    columns=["libelle_region", "libelle_grand_secteur"],
    drop_first=True,
)

# ----------------------------------------------------
# 3. Découpage Temporel Train / Test
# ----------------------------------------------------
# Train : Années < 2024 | Test : Années >= 2024
train_mask = df_ml_encoded["annee"] < 2024
test_mask = df_ml_encoded["annee"] >= 2024

features = [
    c
    for c in df_ml_encoded.columns
    if c not in ["annee", "consommation_mwh"]
]
target = "consommation_mwh"

X_train, y_train = (
    df_ml_encoded.loc[train_mask, features],
    df_ml_encoded.loc[train_mask, target],
)
X_test, y_test = (
    df_ml_encoded.loc[test_mask, features],
    df_ml_encoded.loc[test_mask, target],
)

print(f"   ├─ Ensemble d'entraînement (Train) : {len(X_train)} échantillons")
print(f"   └─ Ensemble de test (Test)         : {len(X_test)} échantillons")

# ----------------------------------------------------
# 4. Entraînement du Modèle Machine Learning
# ----------------------------------------------------
print("\n🤖 Entraînement du modèle Random Forest Regressor...")
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Prédictions
y_pred = model.predict(X_test)

# ----------------------------------------------------
# 5. Évaluation des Performances
# ----------------------------------------------------
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n📊 RÉSULTATS DU MODÈLE SUR L'ENSEMBLE DE TEST (2024-2025) :")
print("-" * 50)
print(f"  • Erreur Absolue Moyenne (MAE) : {mae:,.2f} MWh")
print(f"  • Racine de l'Erreur Quadratique (RMSE) : {rmse:,.2f} MWh")
print(f"  • Coefficient de Détermination (R²)   : {r2:.4f}")
print("-" * 50)

# ----------------------------------------------------
# 6. Visualisation : Valeurs Réelles vs Prédictions
# ----------------------------------------------------
plt.figure(figsize=(10, 6))
sns.scatterplot(x=y_test / 1e3, y=y_pred / 1e3, alpha=0.7, color="tab:blue")
plt.plot(
    [y_test.min() / 1e3, y_test.max() / 1e3],
    [y_test.min() / 1e3, y_test.max() / 1e3],
    "r--",
    lw=2,
    label="Prédiction Parfaite (Y = X)",
)

plt.title("Prédiction de Consommation de Gaz (Modèle Random Forest)")
plt.xlabel("Consommation Réelle (en milliers de MWh)")
plt.ylabel("Consommation Prédite (en milliers de MWh)")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()

# Sauvegarde du graphique
output_fig = "reports/ml_prediction_results.png"
import os

os.makedirs("reports", exist_ok=True)
plt.savefig(output_fig, dpi=300)
print(f"\n🖼️ Graphique d'évaluation sauvegardé dans : {output_fig}")