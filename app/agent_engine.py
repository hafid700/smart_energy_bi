import os
import re
import urllib
import pandas as pd
from openai import OpenAI
from sqlalchemy import create_engine, text

# ----------------------------------------------------
# 1. Configuration de la connexion SQL Server
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

# ----------------------------------------------------
# 2. Contexte du Schéma transmis au LLM (System Prompt)
# ----------------------------------------------------
SCHEMA_CONTEXT = """
Tu es un expert Data Engineer et T-SQL pour Microsoft SQL Server sur la base 'DW_Smart_Energy'.
Génère UNIQUEMENT une requête T-SQL valide sans bloc Markdown (pas de ```sql ... ```), juste le texte brut de la requête SQL.

Voici le schéma exact des tables :

1. Fait_Consommation_Gaz (id_fait, id_temps, id_geographie, id_secteur_activite, consommation_mwh, nombre_pdl, taux_pdl_telereleves)
2. Dim_Geographie (id_geographie, code_iris, nom_commune, code_departement, libelle_departement, libelle_region)
3. Dim_Secteur_Activite (id_secteur_activite, code_categorie, libelle_grand_secteur)
4. Dim_Temps (id_temps, annee)
5. Fait_Prediction_Gaz (id_prediction, annee, libelle_region, libelle_grand_secteur, consommation_mwh, type_donnee) -- type_donnee: 'Réel' ou 'Projection ML'
6. Fait_Anomalie_Gaz (id_anomalie, annee, libelle_region, libelle_grand_secteur, consommation_mwh, z_score, statut_anomalie) -- statut_anomalie: 'Critique', 'Modérée', 'Normale'

Règles de sécurité et syntaxe T-SQL :
- Utilise TOUJOURS 'SELECT' ou 'WITH'. Interdiction absolue d'exécuter INSERT, UPDATE, DELETE, DROP, ALTER.
- Respecte la syntaxe T-SQL de SQL Server (ex: TOP N au lieu de LIMIT N).
- Ne fais jamais d'hallucinations sur les noms de colonnes.

Règles de filtrage strictes :
- Les libellés de régions dans la base sont TOUJOURS en majuscules et SANS ACCENTS (ex: 'ILE-DE-FRANCE', 'HAUTS-DE-FRANCE', 'AUVERGNE-RHONE-ALPES', 'GRAND EST', 'BRETAGNE').
- Pour filtrer sur les régions, transforme toujours la valeur en majuscules et sans accents, ou utilise UPPER() / LIKE '%ILE-DE-FRANCE%'.
- Ne filtre JAMAIS avec des caractères accentués comme 'Île-de-France'.

"""


class SmartEnergyAgent:

    def __init__(self, openrouter_api_key: str):
        # Initialisation du client OpenAI configuré sur les serveurs OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )
        self.model = "nemotron-3-ultra-550b-a55b:free"  # ou "google/gemini-2.0-flash-001", "openai/gpt-4o-mini"

    def _clean_sql(self, sql_raw: str) -> str:
        """Nettoie le texte renvoyé par le LLM pour extraire uniquement le code T-SQL."""
        sql = re.sub(r"```sql\s*", "", sql_raw, flags=re.IGNORECASE)
        sql = re.sub(r"```\s*", "", sql).strip()
        return sql

    def _is_safe_query(self, sql: str) -> bool:
        """Vérification de sécurité pour restreindre aux requêtes de lecture seule."""
        forbidden_keywords = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "ALTER",
            "TRUNCATE",
            "EXEC",
        ]
        sql_upper = sql.upper()
        for kw in forbidden_keywords:
            if re.search(r"\b" + kw + r"\b", sql_upper):
                return False
        return sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")

    def generate_tsql(
        self, user_question: str, previous_error: str = None, failed_sql: str = None
    ) -> str:
        """Génère la requête T-SQL ou adapte la requête si une erreur est survenue."""
        messages = [{"role": "system", "content": SCHEMA_CONTEXT}]

        if previous_error and failed_sql:
            prompt = (
                f"La requête T-SQL suivante a échoué sur SQL Server :\n{failed_sql}\n\n"
                f"Message d'erreur SQL Server :\n{previous_error}\n\n"
                f"Corrige la requête T-SQL pour répondre à la question initiale : '{user_question}'"
            )
        else:
            prompt = f"Question de l'utilisateur : '{user_question}'"

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
        )
        return self._clean_sql(response.choices[0].message.content)

    def execute_agent_loop(self, user_question: str, max_retries: int = 3):
        """Boucle agentique autonome avec auto-correction d'erreurs SQL."""
        last_error = None
        current_sql = None

        for attempt in range(max_retries):
            current_sql = self.generate_tsql(
                user_question,
                previous_error=last_error,
                failed_sql=current_sql,
            )

            # Contrôle de sécurité
            if not self._is_safe_query(current_sql):
                return (
                    None,
                    current_sql,
                    "⚠️ Sécurité : Seules les requêtes SELECT sont autorisées.",
                )

            try:
                # Tentative d'exécution sur SQL Server
                df_result = pd.read_sql(current_sql, engine)
                return df_result, current_sql, None  # Succès !

            except Exception as e:
                last_error = str(e)
                print(
                    f"⚠️ Tentative {attempt + 1} échouée. Erreur SQL : {last_error}"
                )

        return (
            None,
            current_sql,
            f"❌ Échec après {max_retries} tentatives. Erreur : {last_error}",
        )

    def summarize_results(
        self, user_question: str, df_result: pd.DataFrame
    ) -> str:
        """Génère une synthèse décisionnelle en français des données obtenues."""
        data_summary = df_result.head(20).to_string(index=False)
        prompt = (
            f"Tu es un analyste décisionnel expert en énergie (GRDF).\n"
            f"Question initiale : '{user_question}'\n\n"
            f"Résultats extraits de la base DW_Smart_Energy :\n{data_summary}\n\n"
            f"Rédige une réponse synthétique, claire et professionnelle en français avec les chiffrés clés."
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content