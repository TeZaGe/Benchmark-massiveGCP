import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def prepare_data(filename):
    """Charge un CSV, nettoie la colonne AVG_TIME et filtre les échecs."""
    try:
        df = pd.read_csv(filename)
        # Nettoyage : conversion '54ms' -> 54.0
        # On gère le cas où c'est déjà numérique ou string avec 'ms'
        if df['AVG_TIME'].dtype == object:
            df['AVG_TIME_VAL'] = df['AVG_TIME'].astype(str).str.replace('ms', '').astype(float)
        else:
            df['AVG_TIME_VAL'] = df['AVG_TIME']
        
        # On ne garde que les succès (FAILED == 0)
        if 'FAILED' in df.columns:
            df = df[df['FAILED'] == 0]
        return df
    except Exception as e:
        print(f"Attention : Impossible de lire {filename} ({e})")
        return None

# 1. Chargement des données
df_post = prepare_data('csv/post.csv')
df_fanout = prepare_data('csv/fanout.csv')
df_conc = prepare_data('csv/conc.csv')

sns.set_style("whitegrid")

# Configuration des 3 graphiques (chaque entrée produit une image séparée)
configs = [
    {
        'data': df_post,
        'title': 'Impact du nombre de Posts',
        'xlabel': 'Nombre de Posts',
        'color': 'skyblue'
    },
    {
        'data': df_fanout,
        'title': 'Impact du Fanout (Followers)',
        'xlabel': 'Nombre de Followers',
        'color': 'lightgreen'
    },
    {
        'data': df_conc,
        'title': 'Impact de la Charge (Concurrence)',
        'xlabel': 'Clients Simultanés',
        'color': 'salmon'
    }
]

# Dossier de sortie pour les images
out_dir = 'plots'
os.makedirs(out_dir, exist_ok=True)

# 3. Boucle de traçage - une figure par configuration
for idx, config in enumerate(configs, start=1):
    df = config['data']
    title = config['title']

    if df is not None and not df.empty:
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.boxplot(x='PARAM', y='AVG_TIME_VAL', data=df, ax=ax, color=config['color'])

        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel(config['xlabel'])
        ax.set_ylabel('Temps de réponse (ms)')

        # Si l'écart est énorme (ex: Concurrence), on passe en log
        if df['AVG_TIME_VAL'].max() > 2000:
            ax.set_yscale('log')

        plt.tight_layout()

        # Nom de fichier sûr
        safe_title = title.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
        out_path = os.path.join(out_dir, f"plot_{idx}_{safe_title}.png")
        plt.savefig(out_path)
        print(f"Saved plot: {out_path}")
        plt.close(fig)
    else:
        print(f"Aucune donnée pour '{title}' -> saut de la génération d'image.")