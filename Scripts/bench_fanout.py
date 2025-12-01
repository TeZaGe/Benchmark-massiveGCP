import subprocess
import csv
import time
import requests 
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
BASE_URL = "https://massive-gcp-473713.ew.r.appspot.com/api/timeline"
OUTPUT_FILE = "out/fanout.csv"

# Paramètres du test
FOLLOWS_STEPS = [10, 50, 100]
FIXED_POSTS_PER_USER = 100     
NB_USERS = 1000
CONCURRENCY = 50

def run_cmd(cmd):
    print(f"[CMD] {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def benchmark_request(user_idx):
    url = f"{BASE_URL}?user=user{user_idx}"
    try:
        start_time = time.time()
        # Timeout de 5 minutes pour éviter de bloquer indéfiniment
        response = requests.get(url, timeout=300)
        end_time = time.time()

        if response.status_code >= 400:
            return (0, 1)
        
        duration_ms = (end_time - start_time) * 1000
        return (duration_ms, 0)

    except requests.RequestException:
        return (0, 1)

def run():
    sorted_steps = sorted(FOLLOWS_STEPS)
    
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])
        
        current_follows = 0
        
        # 1. NETTOYAGE & INITIALISATION
        print("\n--- INITIALISATION : Clean + Génération de tous les Posts ---")
        try:
            run_cmd("python3 clean.py")
            
            total_posts = NB_USERS * FIXED_POSTS_PER_USER
            print(f"-> Création de {NB_USERS} users et {total_posts} posts...")
            print("-> (Si seed.py utilise le Batch, cela prendra ~10-30 secondes)")
            
            run_cmd(f"python3 seed.py --users {NB_USERS} --posts {total_posts} --follows-min 0 --follows-max 0")
            print("-> Base initialisée avec succès.")
            
        except Exception as e:
            print(f"-> Erreur critique lors de l'init: {e}")
            return

        # 2. BOUCLE SUR LES FOLLOWERS
        for target_follows in sorted_steps:
            follows_needed = target_follows - current_follows
            
            if follows_needed > 0:
                print(f"\n=== Ajout de {follows_needed} followers/user ===")
                # On ajoute juste les relations (posts à 0)
                cmd_seed = (f"python3 seed.py --users {NB_USERS} "
                            f"--posts 0 " 
                            f"--follows-min {follows_needed} --follows-max {follows_needed}")
                run_cmd(cmd_seed)
                current_follows = target_follows
            
            # 3. BENCHMARK PYTHON REQUESTS
            print(f"-> Benchmark {target_follows} Followers (Threads: {CONCURRENCY})")
            
            for run_id in range(1, 4):
                times = []
                failed_count = 0

                with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
                    futures = {executor.submit(benchmark_request, uid): uid for uid in range(1, CONCURRENCY + 1)}
                    
                    for future in as_completed(futures):
                        t_ms, is_failed = future.result()
                        if is_failed:
                            failed_count += 1
                        else:
                            times.append(t_ms)

                # Calcul moyenne
                if times:
                    avg_val = sum(times) / len(times)
                    avg_time_str = f"{avg_val:.2f}"
                else:
                    avg_time_str = "0"
                    
                is_run_failed = 1 if failed_count > 0 else 0
                
                print(f"   Run {run_id}: {avg_time_str} ms | Fail: {failed_count}/{CONCURRENCY}")
                writer.writerow([target_follows, avg_time_str, run_id, is_run_failed])
                f.flush()
                time.sleep(1)

    print("\n--- Benchmark Fanout Terminé ---")

if __name__ == '__main__':
    run()