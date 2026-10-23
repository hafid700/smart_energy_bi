import os
import pandas as pd

# Chemin vers le fichier CSV téléchargé
# Assure-toi de mettre le nom exact de ton fichier CSV téléchargé
CSV_FILE_PATH = "data/raw/consommation-annuelle-de-gaz-par-iris-et-code-naf0.csv"


def inspect_local_csv(file_path):
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé : {file_path}")
        print(
            "👉 Place le fichier téléchargé dans le dossier 'data/raw/' ou ajuste le chemin dans le script."
        )
        return None

    print(f"📖 Lecture du fichier CSV local : {file_path}...")

    # Chargement avec le séparateur point-virgule (;)
    df = pd.read_csv(file_path, sep=";", low_memory=False)

    print("\n✅ Chargement réussi !")
    print(f"📊 Dimensions du jeu de données : {len(df):,} lignes x {len(df.columns)} colonnes")

    print("\n📌 Liste complète des colonnes :")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i}. {col}")

    print("\n🔍 Aperçu des 3 premières lignes :")
    print(df.head(3).T)  # Transposé pour une meilleure lisibilité dans le terminal

    return df


if __name__ == "__main__":
    inspect_local_csv(CSV_FILE_PATH)