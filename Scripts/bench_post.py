import subprocess
import csv
import time
import threading
import requests  
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
BASE_URL = "https://massive-gcp-473713.ew.r.appspot.com/api/timeline"
OUTPUT_FILE = "out/post.csv"

POSTS_STEPS = [10, 100, 1000] 
NB_USERS = 1000
FOLLOWERS = 20
CONCURRENCY = 50

def run_cmd(cmd):
    subprocess.run(cmd, shell=True, check=True)

def benchmark_request(user_idx):
    url = f"{BASE_URL}?user=user{user_idx}"
    try:
        start_time = time.time()
        # Timeout de 5 minutes
        response = requests.get(url, timeout=300)
        end_time = time.time()

        if response.status_code >= 400:
            return (0, 1)
        
        duration_ms = (end_time - start_time) * 1000
        return (duration_ms, 0)

    except requests.RequestException:
        return (0, 1)

def run():
    sorted_steps = sorted(POSTS_STEPS)
    
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])
        
        current_posts_per_user = 0
        
        #Nettoyage initial
        print("\n--- INITIALISATION : Nettoyage complet de la base ---")
        try:
            run_cmd("python3 clean.py")
        except Exception as e:
            print(f"-> Erreur critique clean: {e}")
            return

        for target_posts in sorted_steps:
            posts_needed_per_user = target_posts - current_posts_per_user
            
            if posts_needed_per_user > 0:
                total_new_posts = posts_needed_per_user * NB_USERS
                print(f"\n=== Ajout de {posts_needed_per_user} posts/user (Total: {total_new_posts}) ===")
                
                cmd_seed = (f"python3 seed.py --users {NB_USERS} "
                            f"--posts {total_new_posts} "
                            f"--follows-min {FOLLOWERS} --follows-max {FOLLOWERS}")
                run_cmd(cmd_seed)
                current_posts_per_user = target_posts
            
            # BENCHMARK PYTHON REQUESTS
            print(f"-> Benchmark {target_posts} Posts/User (Threads: {CONCURRENCY})")
            
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
                writer.writerow([target_posts, avg_time_str, run_id, is_run_failed])
                f.flush()
                time.sleep(1)

    print("\n--- Benchmark terminé ---")

if __name__ == '__main__':
    run()