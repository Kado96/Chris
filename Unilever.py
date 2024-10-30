import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap, Fullscreen, Draw
from streamlit_folium import folium_static
import plotly.express as px
from datetime import date, timedelta
from UI import *
from add_data import *
import plotly.graph_objects as go
import io

# Configuration de la page
st.set_page_config(page_title="UNILEVER", page_icon="🌍", layout="wide")
st.header(":bar_chart: Unilever Dashboard")

# Load Style CSS
with open('style.css') as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load Excel file directly
file_path = 'Unilever_-_all_versions_-_labels_-_2024-10-29-12-31-02.xlsx'
df_unilever = pd.read_excel(file_path, sheet_name='Unilever')
df_gpi = pd.read_excel(file_path, sheet_name='GPI')
df_sondage = pd.read_excel(file_path, sheet_name='Sondage')

# Sélection des colonnes spécifiques
df_unilever_cols = ["_index", "_submission_time", "Nom et prénom de l'agent", "Nom de l'établissement", 
                    "Propriètaire", "Type du PDV", "Province", "Commune", "Quartier", 
                    "Adresse du PDV", "Le point de vente est-il nouveau ou ancien?", 
                    "Quels sont vos commentaires généraux ou ceux du vendeur sur le point de vente?",
                    "_Prendre les coordonnées du point de vente_latitude",
                    "_Prendre les coordonnées du point de vente_longitude"]
df_gpi_cols = ["_index", "Selectionner Parmis ces categories"]
df_sondage_cols = ["_index", "Sorte_caracteristic", "Prix de vente unitaire de ${Sorte_caracteristic}", 
                   "Quantite totale de ${Sorte_caracteristic}", "Prix de vente total de ${Sorte_caracteristic}"]

# Extraire seulement les colonnes nécessaires pour réduire la taille des DataFrames
df_unilever = df_unilever[df_unilever_cols]
df_gpi = df_gpi[df_gpi_cols]
df_sondage = df_sondage[df_sondage_cols]

# Fusionner les DataFrames (corriger l'identifiant de fusion si nécessaire)
df_merged = pd.merge(df_unilever, df_gpi, on='_index', how='left')
df_merged = pd.merge(df_merged, df_sondage, on='_index', how='left')

# Filtrage par date
date1 = st.sidebar.date_input("Choisissez une date de début")
date2 = st.sidebar.date_input("Choisissez une date de fin")
date1 = pd.to_datetime(date1)
date2 = pd.to_datetime(date2) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
df_filtered = df_merged[(df_merged["_submission_time"] >= date1) & (df_merged["_submission_time"] <= date2)]

# Filtres supplémentaires
st.sidebar.header("Filtres supplémentaires :")
filters = {
    "Commune": st.sidebar.multiselect("Commune", sorted(df_filtered["Commune"].unique())),
    "Quartier": st.sidebar.multiselect("Quartier", sorted(df_filtered["Quartier"].unique())),
    "Nom et prénom de l'agent": st.sidebar.multiselect("Agent", sorted(df_filtered["Nom et prénom de l'agent"].unique())),
    "Selectionner Parmis ces categories": st.sidebar.multiselect("Categorie produit", sorted(df_filtered["Selectionner Parmis ces categories"].unique())),
    "Sorte_caracteristic": st.sidebar.multiselect("Produit", sorted(df_filtered["Sorte_caracteristic"].astype(str).unique()))  # Conversion en str
}

for col, selection in filters.items():
    if selection:
        df_filtered = df_filtered[df_filtered[col].isin(selection)]

# Bloc analytique
with st.expander("VIEW EXCEL DATASET"):
    showData = st.multiselect('Filter: ', df_filtered.columns, default=df_unilever_cols)
    st.dataframe(df_filtered[showData], use_container_width=True)


# Convertir le DataFrame filtré en un fichier Excel en mémoire
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_filtered.to_excel(writer, index=False)

# Obtenir le contenu du fichier Excel en mémoire
processed_data = output.getvalue()

# Bouton pour télécharger les données filtrées en format Excel avec une clé unique
st.download_button(
    label="📥 Télécharger les données filtrées en format Excel",
    data=processed_data,
    file_name="données_filtrées.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="download_filtered_data"  # Clé unique pour éviter les conflits d'ID
)

# Affichage de la carte
with st.expander("Mapping"):
    if df_filtered['_Prendre les coordonnées du point de vente_latitude'].isnull().all() or \
       df_filtered['_Prendre les coordonnées du point de vente_longitude'].isnull().all():
        st.error("Les coordonnées de localisation sont toutes manquantes.")
    else:
        latitude_mean = df_filtered['_Prendre les coordonnées du point de vente_latitude'].mean()
        longitude_mean = df_filtered['_Prendre les coordonnées du point de vente_longitude'].mean()
        m = folium.Map(location=[latitude_mean, longitude_mean], zoom_start=4)
        marker_cluster = MarkerCluster().add_to(m)

        for _, row in df_filtered.iterrows():
            if pd.notnull(row['_Prendre les coordonnées du point de vente_latitude']) and \
               pd.notnull(row['_Prendre les coordonnées du point de vente_longitude']):
                popup_content = f"""
                <h3>Information of {row['Propriètaire']}</h3>
                <div style='color:gray; font-size:14px;'>
                    <b>Type du PDV:</b> {row['Type du PDV']}
                </div>
                """
                folium.Marker(
                    location=[row['_Prendre les coordonnées du point de vente_latitude'], 
                              row['_Prendre les coordonnées du point de vente_longitude']],
                    tooltip=row['Propriètaire'],
                    icon=folium.Icon(color='red', icon='fa-dollar-sign', prefix='fa')
                ).add_to(marker_cluster).add_child(folium.Popup(popup_content, max_width=600))

        heat_data = [[row['_Prendre les coordonnées du point de vente_latitude'], 
                      row['_Prendre les coordonnées du point de vente_longitude']] 
                     for _, row in df_filtered.iterrows()
                     if pd.notnull(row['_Prendre les coordonnées du point de vente_latitude']) and 
                        pd.notnull(row['_Prendre les coordonnées du point de vente_longitude'])]
        if heat_data:
            HeatMap(heat_data).add_to(m)
        Fullscreen(position='topright').add_to(m)
        Draw(export=True).add_to(m)
        folium_static(m)

# Load dataset and filters
UI()

# Explorateur de DataFrame
def dataframe_explorer(df, case=True):
    filter_column = st.selectbox("Filter dataframe on", df.columns)  # Utilisez df ici
    filter_value = st.text_input("Valeur de filtre")
    if filter_value:
        # Utiliser df_filtered au lieu de df1 et appliquer la logique de filtrage
        filtered_df = df[df[filter_column].astype(str).str.contains(filter_value, case=False, na=False)] if case else \
                      df[df[filter_column].astype(str).str.contains(filter_value, na=False)]
    else:
        filtered_df = df  # Aucune filtration si aucune valeur de filtre n'est donnée
    return filtered_df

# Filtrage et affichage des données
with st.expander("Filter Excel Dataset"):
    filtered_df = dataframe_explorer(df_filtered, case=False)
    st.dataframe(filtered_df, use_container_width=True)

# Convertir le DataFrame filtré en un fichier Excel en mémoire
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    filtered_df.to_excel(writer, index=False)
processed_data = output.getvalue()

# Bouton pour télécharger les données filtrées en format Excel
st.download_button(
    label="📥 Télécharger les données filtrées en format Excel",
    data=processed_data,
    file_name="données_filtrées.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Graphiques
col1, col2 = st.columns(2)

with col1:
    fig2 = go.Figure(
        data=[go.Bar(x=filtered_df['Sorte_caracteristic'].astype(str),  # Conversion en str
                      y=filtered_df['Prix de vente total de ${Sorte_caracteristic}'].astype(float))],
        layout=go.Layout(
            title=go.layout.Title(text="BUSINESS TYPE BY QUARTILES OF INVESTMENT"),
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            xaxis=dict(showgrid=True, gridcolor='#cecdcd'),
            yaxis=dict(showgrid=True, gridcolor='#cecdcd'),
            font=dict(color='#cecdcd'),
        )
    )
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    fig = px.pie(filtered_df, values='Prix de vente total de ${Sorte_caracteristic}', 
                  names='Sorte_caracteristic', title='TotalPrice by Name')
    fig.update_traces(hole=0.4)
    fig.update_layout(width=800)
    st.plotly_chart(fig, use_container_width=True)

# Gestion des erreurs
try:
    pass  # Vous pouvez ajouter votre logique ici si nécessaire
except:
    st.error("Unable to display null, select at least one business location")
