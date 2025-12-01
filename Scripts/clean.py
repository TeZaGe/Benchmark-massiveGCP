from google.cloud import datastore

def cleanup():
    client = datastore.Client()
    kinds = ['Post', 'User'] 
    print("--- Démarrage du nettoyage complet ---")

    for kind in kinds:
        print(f"Récupération des clés pour '{kind}'...")
        query = client.query(kind=kind)
        query.keys_only()

        keys = list(query.fetch())
        total = len(keys)

        if total == 0:
            print(f"Aucune entité '{kind}' à supprimer.")
            continue
        print(f"Suppression de {total} entités '{kind}'...")
        # Suppression par lots de 400 
        batch_size = 400
        for i in range(0, total, batch_size):
            batch = keys[i:i + batch_size]
            client.delete_multi(batch)
            if i % 4000 == 0 and i > 0:
                print(f"   ... {i}/{total} supprimés")
    print("--- Nettoyage terminé avec succès ---")

if __name__ == '__main__':
    cleanup()