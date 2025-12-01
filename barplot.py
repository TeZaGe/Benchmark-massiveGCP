import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def prepare_data(filepath):
    """Charge un CSV, nettoie la colonne AVG_TIME et filtre les échecs."""
    try:
        if not os.path.exists(filepath):
            print(f"Attention : Le fichier {filepath} n'existe pas.")
            return None

        df = pd.read_csv(filepath)
        
        # Nettoyage : conversion '54ms' -> 54.0
        if 'AVG_TIME' in df.columns:
            if df['AVG_TIME'].dtype == object:
                df['AVG_TIME_VAL'] = df['AVG_TIME'].astype(str).str.replace('ms', '').astype(float)
            else:
                df['AVG_TIME_VAL'] = df['AVG_TIME']
        else:
            print(f"Colonne AVG_TIME manquante dans {filepath}")
            return None
        
        # On ne garde que les succès (FAILED == 0)
        if 'FAILED' in df.columns:
            df = df[df['FAILED'] == 0]
            
        return df
    except Exception as e:
        print(f"Erreur lors de la lecture de {filepath} ({e})")
        return None

def generer_graphiques(source_folder, output_folder='plots'):
    """
    Génère les graphiques à partir des CSV situés dans source_folder.
    """
    print(f"\n--- Traitement du dossier : {source_folder} ---")

    # 1. Chargement des données avec chemin dynamique
    # On utilise os.path.join pour gérer correctement les chemins (windows/linux)
    df_post = prepare_data(os.path.join(source_folder, 'post.csv'))
    df_fanout = prepare_data(os.path.join(source_folder, 'fanout.csv'))
    df_conc = prepare_data(os.path.join(source_folder, 'conc.csv'))

    sns.set_style("whitegrid")

    # Configuration des 3 graphiques
    configs = [
        {
            'data': df_post,
            'title': f'Impact du nombre de Posts ({source_folder})',
            'xlabel': 'Nombre de Posts',
            'color': 'skyblue'
        },
        {
            'data': df_fanout,
            'title': f'Impact du Fanout ({source_folder})',
            'xlabel': 'Nombre de Followers',
            'color': 'lightgreen'
        },
        {
            'data': df_conc,
            'title': f'Impact de la Charge ({source_folder})',
            'xlabel': 'Clients Simultanés',
            'color': 'salmon'
        }
    ]

    # Création du dossier de sortie s'il n'existe pas
    os.makedirs(output_folder, exist_ok=True)

    # 3. Boucle de traçage
    generated_count = 0
    for idx, config in enumerate(configs, start=1):
        df = config['data']
        title = config['title']

        if df is not None and not df.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Vérification que la colonne PARAM existe pour l'axe X
            if 'PARAM' in df.columns:
                # On trace un barplot de la moyenne par PARAM (avec erreur type écart-type)
                sns.barplot(x='PARAM', y='AVG_TIME_VAL', data=df, ax=ax, color=config['color'], ci='sd')

                ax.set_title(title, fontsize=12, fontweight='bold')
                ax.set_xlabel(config['xlabel'])
                ax.set_ylabel('Temps de réponse (ms)')

                # Log scale si valeurs très grandes
                if df['AVG_TIME_VAL'].max() > 2000:
                    ax.set_yscale('log')

                # Annoter chaque barre avec la valeur moyenne arrondie
                for p in ax.patches:
                    try:
                        height = p.get_height()
                        if height is None:
                            continue
                        ax.annotate(f"{int(height)}ms",
                                    (p.get_x() + p.get_width() / 2., height),
                                    ha='center', va='bottom', fontsize=9, color='black',
                                    xytext=(0, 4), textcoords='offset points')
                    except Exception:
                        pass

                plt.tight_layout()

                # Nom de fichier sûr incluant le nom du dossier source pour éviter les écrasements
                safe_folder_name = os.path.basename(os.path.normpath(source_folder))
                safe_title = title.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                
                filename = f"plot_{safe_folder_name}_{idx}.png"
                out_path = os.path.join(output_folder, filename)
                
                plt.savefig(out_path)
                print(f"Graphique sauvegardé : {out_path}")
                generated_count += 1
            else:
                print(f"Erreur: Colonne 'PARAM' manquante pour {title}")
            
            plt.close(fig)
        else:
            print(f"Pas de données utilisables pour '{title}'.")

    if generated_count == 0:
        print("Aucun graphique n'a été généré. Vérifiez vos fichiers CSV.")

# --- Point d'entrée du script ---
if __name__ == "__main__":
    # Demande à l'utilisateur quel dossier utiliser
    user_input = input("Entrez le nom du dossier contenant les CSV (ex: old, out, csv) : ").strip()
    
    if user_input:
        # Vérifie si le dossier existe avant de lancer
        if os.path.isdir(user_input):
            generer_graphiques(user_input)
        else:
            print(f"Erreur : Le dossier '{user_input}' est introuvable.")
    else:
        # Valeur par défaut si l'utilisateur appuie juste sur Entrée
        print("Aucune entrée détectée, utilisation du dossier par défaut 'csv'")
        if os.path.isdir('csv'):
            generer_graphiques('csv')
        else:
            print("Le dossier 'csv' par défaut n'existe pas.")