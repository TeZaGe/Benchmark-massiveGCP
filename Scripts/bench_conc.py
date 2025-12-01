import subprocess
import csv
import time
import argparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
BASE_URL = "https://massive-gcp-473713.ew.r.appspot.com/api/timeline"
OUTPUT_FILE = "out/conc.csv"

# Niveaux de concurrence à tester
PARAMS = [1, 10, 20, 50, 100, 1000] 
NB_USERS_DB = 1000
NB_POSTS_PER_USER = 50
NB_FOLLOWS = 20

def run_cmd(cmd):
    print(f"[CMD] {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def benchmark_request(user_idx):
    url = f"{BASE_URL}?user=user{user_idx}"
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        end_time = time.time()

        if response.status_code >= 400:
            return (0, 1)
        
        duration_ms = (end_time - start_time) * 1000
        return (duration_ms, 0)

    except requests.RequestException:
        return (0, 1)

def run():
    # 1. INITIALISATION DES DONNÉES
    print("\n--- INITIALISATION : Préparation de la base pour le test de charge ---")
    try:
        run_cmd("python3 clean.py")
        
        total_posts = NB_USERS_DB * NB_POSTS_PER_USER
        print(f"-> Création de {NB_USERS_DB} users, {total_posts} posts, {NB_FOLLOWS} follows/user...")
        
        run_cmd(f"python3 seed.py --users {NB_USERS_DB} "
                f"--posts {total_posts} "
                f"--follows-min {NB_FOLLOWS} --follows-max {NB_FOLLOWS}")
        print("-> Base prête.")
    except Exception as e:
        print(f"-> Erreur critique init: {e}")
        return

    # 2. BOUCLE DE TEST DE CHARGE
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])

        for concurrency in PARAMS:
            c = concurrency
            target_count = min(c, NB_USERS_DB)
            
            print(f"\n--- Test Concurrence: {c} (Threads actifs: {target_count}) ---")

            for run_id in range(1, 4):
                times = []
                failed_count = 0

                # Lancement des requêtes en parallèle
                with ThreadPoolExecutor(max_workers=target_count) as executor:
                    futures = {executor.submit(benchmark_request, uid): uid for uid in range(1, target_count + 1)}
                    
                    for future in as_completed(futures):
                        t_ms, is_failed = future.result()
                        if is_failed:
                            failed_count += 1
                        else:
                            times.append(t_ms)

                # Calcul des statistiques
                if times:
                    avg_val = sum(times) / len(times)
                    avg_time_str = f"{avg_val:.2f}"
                else:
                    avg_time_str = "0"
                
                # Gestion de l'échec global du run
                is_run_failed = 1 if failed_count > 0 else 0
                
                print(f"   Run {run_id}: {avg_time_str} ms | Fail: {failed_count}/{target_count}")
                writer.writerow([c, avg_time_str, run_id, is_run_failed])
                f.flush()
                
                time.sleep(2)

    print("\n--- Benchmark Concurrence Terminé ---")

if __name__ == '__main__':
    run()