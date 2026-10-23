# ⚡ Smart Energy BI & Predictive Analytics (GRDF Data Warehouse)

Un projet complet d'ingénierie de données (Data Engineering), de Business Intelligence (BI) et de Machine Learning axé sur l'analyse et la prédiction des consommations annuelles de gaz naturel en France (données ouvertes GRDF).

---

## 📌 Vue d'ensemble du projet

L'objectif de ce projet est de concevoir un pipeline décisionnel de bout en bout :

1. **ETL & Data Pipelines :** extraction, nettoyage et transformation d'un jeu de données de ~1 million de lignes.
2. **Data Warehousing :** conception d'un modèle en étoile (*Star Schema*) sous **Microsoft SQL Server**.
3. **Business Intelligence :** création d'un tableau de bord interactif sous **Power BI** pour piloter les consommations et le déploiement des compteurs télérelevés.
4. **Machine Learning :** modèle prédictif (*Random Forest Regressor*) pour anticiper la demande énergétique par région et grand secteur d'activité ($R^2 = 0.9962$).

---

## 🏗️ Architecture du système

```text
[ Données brutes GRDF (CSV) ]
            │
            ▼  (Python / Pandas)
[ Script ETL & Cleaning ]
            │
            ▼  (PyODBC – ingestion rapide)
[ Data Warehouse SQL Server ]
   (Star Schema : Dim_Temps, Dim_Geographie, Dim_Secteur_Activite, Fait_Consommation_Gaz)
            │
            ├───► [ Dashboard Power BI ]
            │        KPIs, analyses temporelles, sectorielles et régionales
            │
            └───► [ Moteur ML Python ]
                     Random Forest Regressor (prédiction en MWh)
```

---

## 📊 Modèle de données (Star Schema SQL Server)

| Table | Rôle |
|---|---|
| **`Fait_Consommation_Gaz`** | ~991k enregistrements (consommation en MWh, nombre de PDL, taux de télérelève) |
| **`Dim_Geographie`** | IRIS, communes, EPCI, départements, régions |
| **`Dim_Secteur_Activite`** | Catégories NAF, grands secteurs (résidentiel, tertiaire, industrie, etc.) |
| **`Dim_Temps`** | Suivi historique multi-années |

---

## 📈 Dashboard Power BI

Le tableau de bord permet une exploration multidimensionnelle :

- **Suivi des KPIs clés :** consommation totale (MWh), volume de Points de Livraison (PDL), taux moyen de télérelève (78 %).
- **Séries temporelles dynamiques :** analyse de la tendance temporelle globale.
- **Ventilation sectorielle & régionale :** comparaison des volumes par secteur d'activité et par région (Île-de-France, Hauts-de-France, Auvergne-Rhône-Alpes, etc.).

---

## 🤖 Performances du modèle Machine Learning

Le modèle prédictif repose sur un **Random Forest Regressor**, entraîné sans fuite temporelle (*Time-Based Split*) :

- **Ensemble d'entraînement (Train) :** données antérieures à 2024.
- **Ensemble de test (Test) :** années 2024–2025.

### Métriques d'évaluation

| Métrique | Valeur |
|---|---|
| Coefficient de détermination ($R^2$) | `0.9962` |
| Erreur absolue moyenne (MAE) | `198 992.28 MWh` |
| Racine de l'erreur quadratique moyenne (RMSE) | `317 420.53 MWh` |

---

## 🚀 Utilisation & déploiement

### 1. Cloner le projet

```bash
git clone https://github.com/votre-username/smart_energy_bi.git
cd smart_energy_bi
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Exécuter l'ingestion dans SQL Server

```bash
python scripts/05_clean_grdf.py
python scripts/dataLoad_dw_sqlServer.py
```

### 4. Lancer le modèle prédictif Machine Learning

```bash
python scripts/06_ml_predict_consumption.py
```

---

## 🛠️ Stack technique

- **Langage :** Python (Pandas, scikit-learn, PyODBC)
- **Base de données :** Microsoft SQL Server
- **BI :** Power BI
- **Source de données :** données ouvertes GRDF