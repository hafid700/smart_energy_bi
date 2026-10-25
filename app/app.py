import os
import plotly.express as px
import streamlit as st
from agent_engine import SmartEnergyAgent
from dotenv import load_dotenv

load_dotenv()

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Smart Energy AI Copilot",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Copilote Analytics & Agent IA — Smart Energy BI")
st.caption(
    "Interrogation intelligente du Data Warehouse GRDF (Text-to-SQL avec Auto-Correction)"
)

# Sidebar : Clé API OpenRouter
with st.sidebar:
    st.header("🔑 Configuration")
    
    openrouter_key = st.text_input(
        "Clé API OpenRouter",
        type="password",
        value=os.getenv("OPENROUTER_API_KEY", ""),
    )
    st.markdown("---")
    st.markdown("### 💡 Exemples de Questions :")
    st.markdown(
        "- *Quelles sont les 3 régions les plus énergivores en 2025 ?*"
    )
    st.markdown(
        "- *Affiche la projection de consommation pour 2026 et 2027 par secteur.*"
    )
    st.markdown(
        "- *Quelles sont les anomalies critiques détectées en Île-de-France ?*"
    )

if not openrouter_key:
    st.info("👈 Veuillez saisir votre clé API OpenRouter dans la barre latérale pour activer le copilote.")
    st.stop()

# Initialisation de l'Agent et de l'historique du Chat
agent = SmartEnergyAgent(openrouter_api_key=openrouter_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des messages passés
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "sql" in msg:
            with st.expander("🔍 Requête T-SQL exécutée"):
                st.code(msg["sql"], language="sql")
        if "data" in msg and msg["data"] is not None:
            st.dataframe(msg["data"])

# Entrée Utilisateur
user_input = st.chat_input("Posez votre question sur les données énergétiques...")

if user_input:
    # Affichage immédiat du message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Réponse de l'Agent
    with st.chat_message("assistant"):
        with st.spinner("🤖 Réflexion & Génération de la requête T-SQL..."):
            df_result, sql_query, error = agent.execute_agent_loop(user_input)

        if error:
            st.error(error)
            if sql_query:
                st.code(sql_query, language="sql")
        else:
            with st.spinner("📊 Analyse des résultats et rédaction de la synthèse..."):
                summary = agent.summarize_results(user_input, df_result)

            st.write(summary)

            # Affichage déroulant du SQL pour transparence
            with st.expander("🔍 Requête T-SQL exécutée avec succès"):
                st.code(sql_query, language="sql")

            # Affichage du tableau de données
            st.markdown("##### 📋 Extrait des données SQL Server :")
            st.dataframe(df_result)

            # Auto-génération de graphique si possible
            num_cols = df_result.select_dtypes(include=["number"]).columns
            cat_cols = df_result.select_dtypes(include=["object"]).columns

            if len(num_cols) >= 1 and len(cat_cols) >= 1:
                fig = px.bar(
                    df_result,
                    x=cat_cols[0],
                    y=num_cols[0],
                    color=(
                        cat_cols[1] if len(cat_cols) > 1 else None
                    ),
                    title=f"{num_cols[0]} par {cat_cols[0]}",
                )
                st.plotly_chart(fig, use_container_width=True)

            # Enregistrement dans l'historique
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": summary,
                    "sql": sql_query,
                    "data": df_result,
                }
            )