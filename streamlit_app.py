
import streamlit as st
from PIL import Image
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from io import BytesIO

# Appliquer du style CSS
st.markdown("""
<style>
h1, h2, h3, h4 { color: #203040; }
.stDataFrame th, .stDataFrame td { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# Afficher le logo en haut de toutes les pages
logo = Image.open("logo_kwilu.png")
st.image(logo, width=200)

# Navigation simple
page = st.sidebar.radio("Navigation", ["🏠 Accueil", "📊 Tableau de bord"])

if page == "🏠 Accueil":
    st.title("Bienvenue sur le Tableau de Bord Commercial de Kwilu Briques")
    st.markdown("""
    Ce tableau de bord vous permet de :
    - Visualiser les indicateurs clés de vente
    - Analyser les quantités commandées et livrées
    - Consulter les remises accordées
    - Télécharger les données complètes au format Excel
    
    Utilisez le menu de navigation à gauche pour accéder aux données.
    """)

else:
    # --- Connexion à la base de données ---
    DB_PATH =  "Donnees_JOUR_ventes.sqlite"
    conn = sqlite3.connect(DB_PATH)

    # --- Titre ---
    st.title("Tableau de bord - Kwilu Briques")

    # --- Sélecteurs année et mois ---
    annees = pd.read_sql("SELECT DISTINCT strftime('%Y', DATE_FACTURE) as annee FROM FACTURE ORDER BY annee", conn)
    annee_selection = st.sidebar.selectbox("Année", annees['annee'])
    mois_selection = st.sidebar.selectbox("Mois", ["Tous"] + [f"{i:02d}" for i in range(1, 13)], index=0)
    where_clause = f"strftime('%Y', DATE_FACTURE) = '{annee_selection}'"
    if mois_selection != "Tous":
        where_clause += f" AND strftime('%m', DATE_FACTURE) = '{mois_selection}'"

    # --- KPI ---
    st.subheader(f"Indicateurs clefs - Année {annee_selection} Mois {mois_selection if mois_selection != 'Tous' else '(tous)'}")
    kpi_query = f"SELECT ROUND(SUM(MONTANT_HTVA), 2) AS CA_HTVA, ROUND(SUM(MONTANT_TVAC), 2) AS CA_TVAC FROM FACTURE WHERE {where_clause}"
    kpi = pd.read_sql(kpi_query, conn)
    st.metric("Chiffre d'affaires HTVA", f"{kpi.CA_HTVA[0]} USD")
    st.metric("Chiffre d'affaires TVAC", f"{kpi.CA_TVAC[0]} USD")

    # --- Graphique CA mensuel ---
    st.subheader("Chiffre d'affaires mensuel")
    ca_mensuel = pd.read_sql(f"SELECT strftime('%m', DATE_FACTURE) as mois, ROUND(SUM(MONTANT_HTVA), 2) AS HTVA, ROUND(SUM(MONTANT_TVAC), 2) AS TVAC FROM FACTURE WHERE strftime('%Y', DATE_FACTURE) = '{annee_selection}' GROUP BY mois ORDER BY mois", conn)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ca_mensuel['mois'], ca_mensuel['HTVA'], label='HTVA')
    ax.plot(ca_mensuel['mois'], ca_mensuel['TVAC'], label='TVAC')
    ax.set_xlabel("Mois", fontsize=12)
    ax.set_ylabel("Montant (USD)", fontsize=12)
    ax.set_title("CA mensuel", fontsize=14)
    ax.legend(fontsize=10)
    st.pyplot(fig)

    # --- Graphiques et Tableaux ---
    st.subheader("Blocs les plus commandés")
    qte_commande_bloc = pd.read_sql("SELECT TB.NOM_BLOC, SUM(DC.QUANTITE_COMMANDEE) AS TOTAL_QTE FROM DETAIL_COMMANDE DC JOIN TYPE_BLOC TB ON DC.ID_TYPE_BLOC = TB.ID_TYPE_BLOC GROUP BY TB.NOM_BLOC ORDER BY TOTAL_QTE DESC", conn)
    st.bar_chart(qte_commande_bloc.set_index('NOM_BLOC'))
    st.dataframe(qte_commande_bloc)

    st.subheader("Blocs les plus livrés")
    qte_livree_bloc = pd.read_sql("SELECT TB.NOM_BLOC, SUM(DL.QUANTITE_LIVREE) AS TOTAL_QTE FROM DETAIL_LIVRAISON DL JOIN TYPE_BLOC TB ON DL.ID_TYPE_BLOC = TB.ID_TYPE_BLOC GROUP BY TB.NOM_BLOC ORDER BY TOTAL_QTE DESC", conn)
    st.bar_chart(qte_livree_bloc.set_index('NOM_BLOC'))
    st.dataframe(qte_livree_bloc)

    st.subheader("Masse cuite moyenne par type de bloc")
    masse = pd.read_sql("SELECT TB.NOM_BLOC, ROUND(AVG(MB.MASSE_CUITE), 2) AS MASSE_MOY FROM MESURES_BLOCS MB JOIN TYPE_BLOC TB ON MB.ID_TYPE_BLOC = TB.ID_TYPE_BLOC GROUP BY TB.NOM_BLOC ORDER BY MASSE_MOY DESC", conn)
    st.dataframe(masse)

    st.subheader("Ventes par client")
    clients = pd.read_sql(f"SELECT C.NOM_CLIENT, COUNT(DISTINCT BC.ID_COMMANDE) AS NB_COMMANDES, ROUND(SUM(F.MONTANT_HTVA), 2) AS CA_HTVA, ROUND(SUM(F.MONTANT_TVAC), 2) AS CA_TVAC FROM CLIENTS C JOIN BON_COMMANDE BC ON C.ID_CLIENT = BC.ID_CLIENT JOIN BON_LIVRAISON BL ON BC.ID_COMMANDE = BL.ID_COMMANDE JOIN FACTURE F ON BL.ID_LIVRAISON = F.ID_LIVRAISON WHERE {where_clause} GROUP BY C.NOM_CLIENT ORDER BY CA_TVAC DESC", conn)
    st.dataframe(clients)

    st.subheader("Remises par client")
    remises_clients = pd.read_sql(f"SELECT C.NOM_CLIENT, COUNT(*) AS NB_COMMANDES, ROUND(SUM(BC.REMISE_MONTANT), 2) AS TOTAL_REMISE FROM BON_COMMANDE BC JOIN CLIENTS C ON BC.ID_CLIENT = C.ID_CLIENT WHERE strftime('%Y', BC.DATE_COMMANDE) = '{annee_selection}' {f"AND strftime('%m', BC.DATE_COMMANDE) = '{mois_selection}'" if mois_selection != 'Tous' else ''} AND BC.REMISE_MONTANT > 0 GROUP BY C.NOM_CLIENT ORDER BY TOTAL_REMISE DESC", conn)
    st.dataframe(remises_clients)

    st.subheader("Commandes détaillées")
    detail_commandes = pd.read_sql(f"SELECT BC.DATE_COMMANDE, C.NOM_CLIENT, TB.NOM_BLOC, DC.QUANTITE_COMMANDEE, DC.PRIX_UNITAIRE_CONVENU, BC.REMISE_MONTANT FROM DETAIL_COMMANDE DC JOIN BON_COMMANDE BC ON DC.ID_COMMANDE = BC.ID_COMMANDE JOIN CLIENTS C ON BC.ID_CLIENT = C.ID_CLIENT JOIN TYPE_BLOC TB ON DC.ID_TYPE_BLOC = TB.ID_TYPE_BLOC WHERE strftime('%Y', BC.DATE_COMMANDE) = '{annee_selection}' {f"AND strftime('%m', BC.DATE_COMMANDE) = '{mois_selection}'" if mois_selection != 'Tous' else ''} ORDER BY BC.DATE_COMMANDE DESC", conn)
    st.dataframe(detail_commandes)

    # --- Export Excel ---
    def to_excel(dfs: dict) -> BytesIO:
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        for sheet_name, df in dfs.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        writer.close()
        output.seek(0)
        return output

    if st.button("📃 Télécharger tous les tableaux en Excel"):
        xlsx_data = to_excel({
            "CA_mensuel": ca_mensuel,
            "Quantites_commandees": qte_commande_bloc,
            "Quantites_livrees": qte_livree_bloc,
            "Masses_blocs": masse,
            "Clients": clients,
            "Remises_clients": remises_clients,
            "Commandes_detaillées": detail_commandes
        })
        st.download_button(
            label="📄 Télécharger le fichier Excel",
            data=xlsx_data,
            file_name=f"Dashboard_Kwilu_{annee_selection}_{mois_selection}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    conn.close()
