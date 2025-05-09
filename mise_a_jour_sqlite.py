import pandas as pd
import sqlite3
import re

# === Chemins ===
excel_path = '/Users/christophecote/Documents/DATA ANALYSIS/ventes/Donnees_JOUR_ventes.xlsx'
db_path = '/Users/christophecote/Documents/DATA ANALYSIS/ventes/Donnees_JOUR_ventes.sqlite'

# === Normalisation du nom de table ===
def normalize_table_name(sheet_name):
    return re.sub(r'\W+', '_', sheet_name.strip())

# === Connexion ===
xls = pd.ExcelFile(excel_path)
conn = sqlite3.connect(db_path)

for sheet in xls.sheet_names:
    print(f'🔄 Traitement de la feuille : {sheet}')
    df_excel = pd.read_excel(xls, sheet_name=sheet)
    if df_excel.empty:
        print(f'⚠️ Feuille vide : {sheet}, ignorée.')
        continue

    # Nettoyage et détection de la colonne ID
    df_excel.columns = df_excel.columns.str.strip()
    id_col = next((col for col in df_excel.columns if col.startswith('ID_')), None)
    if id_col is None:
        print(f'⚠️ Pas de colonne ID_ dans {sheet}, feuille ignorée.')
        continue

    # Nettoyage des IDs dans Excel
    df_excel[id_col] = df_excel[id_col].astype(str).str.strip()

    # Détection des doublons dans Excel lui-même
    duplicates = df_excel[df_excel.duplicated(subset=[id_col], keep=False)]
    if not duplicates.empty:
        print(f'⚠️ {len(duplicates)} doublon(s) détecté(s) dans la feuille Excel {sheet} (valeurs ID identiques)')

    table_name = normalize_table_name(sheet)

    try:
        # Lecture des IDs déjà en base
        df_sql = pd.read_sql(f'SELECT {id_col} FROM "{table_name}"', conn)
        df_sql[id_col] = df_sql[id_col].astype(str).str.strip()

        ids_sql = set(df_sql[id_col])
        df_new = df_excel[~df_excel[id_col].isin(ids_sql)]

        if not df_new.empty:
            df_new.to_sql(table_name, conn, if_exists='append', index=False)
            print(f'✅ {len(df_new)} nouvelles ligne(s) ajoutée(s) à {table_name}.')
        else:
            print(f'⏩ Aucune ligne nouvelle à ajouter pour {table_name}.')

    except Exception as e:
        print(f'❌ Erreur lors du traitement de {table_name} : {e}')

conn.close()
print('✅ Mise à jour de la base de données terminée.')