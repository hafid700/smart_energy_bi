
import pandas as pd

path = "data/raw/consommation-annuelle-de-gaz-par-iris-et-code-naf0.csv"

# Charger le CSV en supprimant automatiquement le BOM
df = pd.read_csv(
    path,
    sep=None,
    engine="python",
    encoding="utf-8-sig"
)

# Nettoyer les noms des colonnes
df.columns = df.columns.str.strip()

print("=" * 60)
print("1. DIMENSIONS DU DATASET")
print("=" * 60)
print("Nombre de lignes :", df.shape[0])
print("Nombre de colonnes :", df.shape[1])

print("\nColonnes détectées :")
for col in df.columns:
    print("-", col)

# Vérifier les années
col_annee = "Année Consommation"

print("\n" + "=" * 60)
print("2. ANNÉES DISPONIBLES")
print("=" * 60)
print(sorted(df[col_annee].dropna().unique()))

# Convertir les mesures en nombres, si nécessaire
colonnes_numeriques = [
    "Consommation Annuelle en MWh",
    "Nombre Points de Livraison",
    "Taux Points de Livraison télérelevés"
]

for col in colonnes_numeriques:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    )

# Valeurs manquantes
print("\n" + "=" * 60)
print("3. VALEURS MANQUANTES")
print("=" * 60)
print(df.isna().sum().sort_values(ascending=False).head(20))

# Statistiques des mesures
print("\n" + "=" * 60)
print("4. STATISTIQUES DES MESURES")
print("=" * 60)

for col in colonnes_numeriques:
    print(f"\n--- {col} ---")
    print(df[col].describe())

# Répartition par secteur
print("\n" + "=" * 60)
print("5. RÉPARTITION PAR SECTEUR")
print("=" * 60)
print(
    df["Libellé Grand Secteur Activité"]
    .value_counts(dropna=False)
)

# Nombre de lignes par année
print("\n" + "=" * 60)
print("6. NOMBRE DE LIGNES PAR ANNÉE")
print("=" * 60)
print(df.groupby(col_annee).size())

# Doublons exacts
print("\n" + "=" * 60)
print("7. DOUBLONS EXACTS")
print("=" * 60)
print("Nombre de doublons :", df.duplicated().sum())

print("\nProfilage terminé.")
