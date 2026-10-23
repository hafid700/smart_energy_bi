
from pathlib import Path
import pandas as pd

# Chemins des fichiers
input_path = Path(
    "data/raw/consommation-annuelle-de-gaz-par-iris-et-code-naf0.csv"
)

output_path = Path(
    "data/processed/grdf_clean.csv"
)

# Créer le dossier de sortie
output_path.parent.mkdir(parents=True, exist_ok=True)

# 1. Charger le dataset
df = pd.read_csv(
    input_path,
    sep=None,
    engine="python",
    encoding="utf-8-sig"
)

# 2. Nettoyer les noms de colonnes
df.columns = df.columns.str.strip()

# 3. Convertir les mesures en valeurs numériques
mesures = [
    "Consommation Annuelle en MWh",
    "Nombre Points de Livraison",
    "Taux Points de Livraison télérelevés"
]

for col in mesures:
    df[col] = pd.to_numeric(
        df[col].astype("string").str.replace(
            ",", ".", regex=False
        ),
        errors="coerce"
    )

# 4. Renommer les colonnes pour faciliter le travail BI
renommage = {
    "Année Consommation": "annee",
    "Code Région Administrative": "code_region",
    "Libellé Région Administrative": "region",
    "Code Département": "code_departement",
    "Libellé Département": "departement",
    "Code EPCI": "code_epci",
    "Libellé EPCI": "epci",
    "Code INSEE Commune": "code_commune",
    "Nom INSEE Commune": "commune",
    "Code IRIS": "code_iris",
    "Libellé IRIS": "iris",
    "Libellé Grand Secteur Activité": "secteur_activite",
    "Code Catégorie": "code_categorie",
    "Code Section NAF": "code_section_naf",
    "Libellé Section NAF": "section_naf",
    "Code Division NAF": "code_division_naf",
    "Libellé Division NAF": "division_naf",
    "Nombre Points de Livraison": "nombre_points_livraison",
    "Consommation Annuelle en MWh": "consommation_mwh",
    "Taux Points de Livraison télérelevés": "taux_teleleve"
}

df = df.rename(columns=renommage)

# 5. Créer des indicateurs de qualité
df["consommation_disponible"] = (
    df["consommation_mwh"].notna()
)

df["points_livraison_disponibles"] = (
    df["nombre_points_livraison"].notna()
)

df["taux_teleleve_disponible"] = (
    df["taux_teleleve"].notna()
)

# 6. Convertir le taux en pourcentage
df["taux_teleleve_pct"] = df["taux_teleleve"] * 100

# 7. Vérifications avant export
print("Dimensions :", df.shape)
print(
    "Consommations manquantes :",
    df["consommation_mwh"].isna().sum()
)
print(
    "Points de livraison manquants :",
    df["nombre_points_livraison"].isna().sum()
)
print(
    "Taux de télérelève manquants :",
    df["taux_teleleve"].isna().sum()
)

# Ne supprimer aucune ligne
df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("\nFichier nettoyé enregistré :", output_path)
print("Nombre de lignes exportées :", len(df))
