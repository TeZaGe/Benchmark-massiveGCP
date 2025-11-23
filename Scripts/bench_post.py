import subprocess
import csv
import os
import re
import time

# --- CONFIGURATION ---
TARGET_URL = "https://massive-gcp-473713.ew.r.appspot.com/"
OUTPUT_FILE = "out/post.csv"
POSTS_PER_USER = [10, 100, 1000] 
NB_USERS = 1000
FOLLOWERS = 20
CONCURRENCY = 50 

def run_cmd(cmd):
    subprocess.run(cmd, shell=True, check=True)

def run():
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])

        for posts_count in POSTS_PER_USER:
            total_posts = NB_USERS * posts_count
            print(f"\n==============================================")
            print(f" PARAMETRE POSTS: {posts_count} (Total DB: {total_posts})")
            print(f"==============================================")

            # 1. CLEAN
            print("-> Nettoyage de la base...")
            run_cmd("python3 clean.py")

            # 2. SEED
            print(f"-> Génération des données ({total_posts} posts)...")
            run_cmd(f"python3 seed.py --users {NB_USERS} --posts {total_posts} --follows-min {FOLLOWERS} --follows-max {FOLLOWERS}")

            # 3. BENCHMARK
            print(f"-> Lancement du benchmark (Concurrence {CONCURRENCY})...")
            for run_id in range(1, 4):
                cmd = f"ab -k -c {CONCURRENCY} -n {CONCURRENCY*2} -t 5 {TARGET_URL}"
                
                avg_time = "0ms"
                failed = 0
                try:
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    match = re.search(r"Time per request:\s+([0-9\.]+)\s+\[ms\]\s+\(mean\)", res.stdout)
                    if match:
                        avg_time = f"{int(float(match.group(1)))}ms"
                    else:
                        failed = 1
                    
                    if "Non-2xx responses" in res.stdout or res.returncode != 0:
                        failed = 1
                except:
                    failed = 1

                print(f"   Run {run_id}: {avg_time} | Failed: {failed}")
                writer.writerow([posts_count, avg_time, run_id, failed])
                f.flush()
                time.sleep(1)

if __name__ == '__main__':
    run()