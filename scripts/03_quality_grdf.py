
import pandas as pd

path = "data/raw/consommation-annuelle-de-gaz-par-iris-et-code-naf0.csv"

df = pd.read_csv(
    path,
    sep=None,
    engine="python",
    encoding="utf-8-sig"
)

df.columns = df.columns.str.strip()

# Conversion des mesures en nombres
mesures = [
    "Consommation Annuelle en MWh",
    "Nombre Points de Livraison",
    "Taux Points de Livraison télérelevés"
]

for col in mesures:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    )

# 1. Valeurs manquantes par secteur
print("\n=== 1. VALEURS MANQUANTES PAR SECTEUR ===")

print(
    df.groupby("Libellé Grand Secteur Activité")[mesures]
    .agg(lambda s: s.isna().sum())
)

# 2. Nombre de lignes et consommations manquantes par année
print("\n=== 2. QUALITÉ PAR ANNÉE ===")

qualite_annee = df.groupby("Année Consommation").agg(
    nombre_lignes=("Année Consommation", "size"),
    consommations_manquantes=(
        "Consommation Annuelle en MWh",
        lambda s: s.isna().sum()
    ),
    consommations_nulles=(
        "Consommation Annuelle en MWh",
        lambda s: s.eq(0).sum()
    )
)

print(qualite_annee.to_string())

# 3. Absence de codes NAF par secteur
print("\n=== 3. CODES NAF MANQUANTS PAR SECTEUR ===")

naf = [
    "Code Section NAF",
    "Code Division NAF",
    "Libellé Section NAF",
    "Libellé Division NAF"
]

print(
    df.groupby("Libellé Grand Secteur Activité")[naf]
    .agg(lambda s: s.isna().sum())
    .to_string()
)

# 4. Vérification de la plage du taux de télérelève
print("\n=== 4. CONTRÔLE DU TAUX DE TÉLÉRELÈVE ===")

taux = df["Taux Points de Livraison télérelevés"].dropna()

print("Minimum :", taux.min())
print("Maximum :", taux.max())
print("Valeurs inférieures à 0 :", (taux < 0).sum())
print("Valeurs supérieures à 1 :", (taux > 1).sum())

# 5. Vérification des combinaisons de dimensions répétées
print("\n=== 5. DOUBLONS POTENTIELS SUR LES DIMENSIONS ===")

dimensions = [
    "Année Consommation",
    "Code IRIS",
    "Code Catégorie",
    "Code Section NAF",
    "Code Division NAF"
]

doublons_dimensions = df.duplicated(
    subset=dimensions,
    keep=False
)

print(
    "Lignes appartenant à une combinaison répétée :",
    doublons_dimensions.sum()
)

print(
    df.loc[doublons_dimensions, dimensions]
    .head(10)
    .to_string(index=False)
)

print("\nContrôle qualité terminé.")
