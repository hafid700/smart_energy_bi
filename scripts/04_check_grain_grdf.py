
import pandas as pd

path = "data/raw/consommation-annuelle-de-gaz-par-iris-et-code-naf0.csv"

df = pd.read_csv(
    path,
    sep=None,
    engine="python",
    encoding="utf-8-sig"
)

df.columns = df.columns.str.strip()

# Colonnes de mesure
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

# Clé candidate utilisant toutes les dimensions disponibles
dimensions = [
    "Année Consommation",
    "Code Région Administrative",
    "Code Département",
    "Code EPCI",
    "Code INSEE Commune",
    "Code IRIS",
    "Libellé Grand Secteur Activité",
    "Code Catégorie",
    "Code Section NAF",
    "Code Division NAF"
]

print("=" * 65)
print("1. RÉPÉTITIONS SUR LA CLÉ CANDIDATE")
print("=" * 65)

nb_groupes_repetes = (
    df.groupby(dimensions, dropna=False)
    .size()
    .gt(1)
    .sum()
)

nb_lignes_groupes_repetes = (
    df.groupby(dimensions, dropna=False)
    .size()
    .loc[lambda s: s > 1]
    .sum()
)

print("Nombre de groupes répétés :", nb_groupes_repetes)
print("Nombre de lignes concernées :", nb_lignes_groupes_repetes)

# Examiner les groupes répétés et leurs mesures
print("\n" + "=" * 65)
print("2. EXEMPLES DE GROUPES RÉPÉTÉS")
print("=" * 65)

group_sizes = (
    df.groupby(dimensions, dropna=False)
    .size()
    .rename("Nombre de lignes")
    .reset_index()
)

repeated_keys = group_sizes.loc[
    group_sizes["Nombre de lignes"] > 1
]

if repeated_keys.empty:
    print("Aucun groupe répété avec cette clé candidate.")
else:
    sample_keys = repeated_keys.head(10)[dimensions]

    sample = df.merge(
        sample_keys,
        on=dimensions,
        how="inner"
    )

    print(
        sample[
            dimensions + mesures
        ].to_string(index=False)
    )

# Contrôler les valeurs négatives
print("\n" + "=" * 65)
print("3. CONTRÔLE DES MESURES NÉGATIVES")
print("=" * 65)

for col in mesures:
    print(
        f"{col} :",
        (df[col] < 0).sum(),
        "valeurs négatives"
    )

# Exporter les groupes répétés pour une analyse ultérieure
repeated_keys.to_csv(
    "data/repeated_candidate_keys.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nRapport des clés candidates répétés enregistré dans :")
print("data/repeated_candidate_keys.csv")
print("\nContrôle terminé. Aucune ligne source n'a été supprimée.")
