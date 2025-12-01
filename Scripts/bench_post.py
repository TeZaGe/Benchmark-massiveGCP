import subprocess
import csv
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
BASE_URL = "https://massive-gcp-473713.ew.r.appspot.com/api/timeline"
OUTPUT_FILE = "out/post.csv"

# Séquence demandée : 10 -> 100 -> 1000 
POSTS_STEPS = [10, 100, 1000] 
NB_USERS = 1000
FOLLOWERS = 20
CONCURRENCY = 50  # 50 Threads simultanés

def run_cmd(cmd):
    """Exécute une commande shell et vérifie qu'elle réussit."""
    subprocess.run(cmd, shell=True, check=True)

def run():
    # On s'assure que la liste est triée pour que l'incrémental fonctionne
    sorted_steps = sorted(POSTS_STEPS)
    
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])
        
        current_posts_per_user = 0
        print_lock = threading.Lock()

        # 1. Nettoyage initial UNIQUE (on part de zéro)
        print("\n--- INITIALISATION : Nettoyage complet de la base ---")
        try:
            run_cmd("python3 clean.py")
            print("-> Base nettoyée.")
        except Exception as e:
            print(f"-> Erreur critique lors du clean: {e}")
            return

        for target_posts in sorted_steps:
            # 2. SEED INCREMENTAL
            # Calcul du delta à ajouter
            posts_needed_per_user = target_posts - current_posts_per_user
            
            if posts_needed_per_user > 0:
                # seed.py prend le nombre TOTAL de posts à répartir
                total_new_posts = posts_needed_per_user * NB_USERS
                
                print(f"\n==============================================")
                print(f" PREPARATION: Passage de {current_posts_per_user} à {target_posts} posts/user")
                print(f" Ajout de {total_new_posts} posts ({posts_needed_per_user} par user sur {NB_USERS} users)")
                print(f"==============================================")
                
                
                cmd_seed = (f"python3 seed.py --users {NB_USERS} "
                            f"--posts {total_new_posts} "
                            f"--follows-min {FOLLOWERS} --follows-max {FOLLOWERS}")
                run_cmd(cmd_seed)
                
                # Mise à jour de l'état actuel
                current_posts_per_user = target_posts
            
            elif posts_needed_per_user < 0:
                print(f"[ERREUR] Impossible de réduire le nombre de posts (Delta négatif).")
                continue

            # 3. BENCHMARK MULTITHREADÉ (Concurrency = 50)
            print(f"-> Lancement du benchmark pour {target_posts} Posts/User (Concurrency: {CONCURRENCY})")
            
            for run_id in range(1, 4):
                with print_lock:
                    print(f"   Run {run_id}/3...")

                def ab_one(user_idx):
                    target_url = f"{BASE_URL}?user=user{user_idx}"
                    # ab : -c 1 -n 1 car la concurrence est gérée par nos threads Python
                    cmd = f"ab -k -c 1 -n 1 -t 5 \"{target_url}\""
                    
                    try:
                        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        output = (res.stdout or "") + "\n" + (res.stderr or "")
                        
                        # Extraction du temps moyen
                        match = re.search(r"Time per request:\s+([0-9\.]+)\s+\[ms\]\s+\(mean\)", output)
                        if match:
                            return (int(float(match.group(1))), 0)
                        else:
                            # Echec de parsing
                            with print_lock:
                                pass
                            return (0, 1)
                    except Exception as e:
                        return (0, 1)

                times = []
                failed_count = 0

                # Lancement des threads (Simulation de 50 clients simultanés)
                with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
                    # On cible les utilisateurs user1 à user50 
                    futures = {executor.submit(ab_one, uid): uid for uid in range(1, CONCURRENCY + 1)}
                    
                    for future in as_completed(futures):
                        t, err = future.result()
                        if err:
                            failed_count += 1
                        else:
                            times.append(t)

                # Calcul de la moyenne globale pour ce Run
                if times:
                    avg_val = int(sum(times) / len(times))
                    avg_time_str = f"{avg_val}ms"
                else:
                    avg_time_str = "0ms"
                    failed_count = CONCURRENCY  # Tout a échoué

                # On considère le run "Failed" si au moins une requête a échoué (optionnel, ou > 1)
                is_run_failed = 1 if failed_count > 0 else 0
                
                print(f"      Result: {avg_time_str} | Failed inst.: {failed_count}/{CONCURRENCY}")
                writer.writerow([target_posts, avg_time_str, run_id, is_run_failed])
                f.flush()
                time.sleep(1)

    print("\n--- Benchmark terminé ---")

if __name__ == '__main__':
    run()