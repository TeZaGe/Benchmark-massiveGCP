import subprocess
import csv
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
BASE_URL = "https://massive-gcp-473713.ew.r.appspot.com/api/timeline"
OUTPUT_FILE = "out/fanout.csv"

# Paramètres du test
FOLLOWS_STEPS = [10, 50, 100]  # On fait varier les followers
FIXED_POSTS_PER_USER = 100     # Fixé à 100 posts
NB_USERS = 1000
CONCURRENCY = 50               # 50 threads simultanés

def run_cmd(cmd):
    """Exécute une commande shell."""
    subprocess.run(cmd, shell=True, check=True)

def run():
    sorted_steps = sorted(FOLLOWS_STEPS)
    
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])
        
        current_follows = 0
        print_lock = threading.Lock()

        # 1. NETTOYAGE & INITIALISATION DES POSTS (LOURD)
        # On nettoie tout, puis on crée les 1000 users et leurs 100 posts CHACUN d'un coup.
        # On met follows à 0 pour l'instant.
        print("\n--- INITIALISATION : Clean + Génération de tous les Posts ---")
        try:
            run_cmd("python3 clean.py")
            
            total_posts = NB_USERS * FIXED_POSTS_PER_USER
            print(f"-> Création de {NB_USERS} users et {total_posts} posts (Follows=0)...")
            
            # On initialise avec 0 followers pour partir d'une base neutre
            run_cmd(f"python3 seed.py --users {NB_USERS} --posts {total_posts} --follows-min 0 --follows-max 0")
            print("-> Base initialisée avec succès.")
            
        except Exception as e:
            print(f"-> Erreur critique lors de l'init: {e}")
            return

        # 2. BOUCLE SUR LES FOLLOWERS (INCREMENTAL)
        for target_follows in sorted_steps:
            # Calcul du nombre de followers à AJOUTER
            follows_needed = target_follows - current_follows
            
            if follows_needed > 0:
                print(f"\n==============================================")
                print(f" PREPARATION: Passage de {current_follows} à ~{target_follows} followers")
                print(f" Ajout de {follows_needed} relations par utilisateur")
                print(f"==============================================")
                
                # seed.py fait une UNION des followers existants et nouveaux.
                # On met --posts 0 car les posts sont déjà là.
                cmd_seed = (f"python3 seed.py --users {NB_USERS} "
                            f"--posts 0 "  # Important : 0 nouveaux posts
                            f"--follows-min {follows_needed} --follows-max {follows_needed}")
                run_cmd(cmd_seed)
                
                current_follows = target_follows
            
            elif follows_needed < 0:
                print(f"[WARN] Impossible de réduire les followers ({current_follows} -> {target_follows}).")
                continue

            # 3. BENCHMARK MULTITHREADÉ
            print(f"-> Lancement du benchmark pour {target_follows} Followers (Concurrency: {CONCURRENCY})")
            
            for run_id in range(1, 4):
                with print_lock:
                    print(f"   Run {run_id}/3...")

                # Fonction worker pour chaque thread
                def ab_one(user_idx):
                    target_url = f"{BASE_URL}?user=user{user_idx}"
                    # ab : -c 1 -n 1 (Concurrency gérée par Python)
                    cmd = f"ab -k -c 1 -n 1 -t 5 \"{target_url}\""
                    
                    try:
                        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        output = (res.stdout or "") + "\n" + (res.stderr or "")
                        match = re.search(r"Time per request:\s+([0-9\.]+)\s+\[ms\]\s+\(mean\)", output)
                        if match:
                            return (int(float(match.group(1))), 0)
                        else:
                            return (0, 1)
                    except:
                        return (0, 1)

                times = []
                failed_count = 0

                # Lancement des 50 threads
                with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
                    futures = {executor.submit(ab_one, uid): uid for uid in range(1, CONCURRENCY + 1)}
                    
                    for future in as_completed(futures):
                        t, err = future.result()
                        if err:
                            failed_count += 1
                        else:
                            times.append(t)

                # Calcul moyenne
                if times:
                    avg_val = int(sum(times) / len(times))
                    avg_time_str = f"{avg_val}ms"
                else:
                    avg_time_str = "0ms"
                    failed_count = CONCURRENCY

                is_run_failed = 1 if failed_count > 0 else 0
                
                print(f"      Result: {avg_time_str} | Failed inst.: {failed_count}/{CONCURRENCY}")
                writer.writerow([target_follows, avg_time_str, run_id, is_run_failed])
                f.flush()
                time.sleep(1)

    print("\n--- Benchmark Fanout Terminé ---")

if __name__ == '__main__':
    run()