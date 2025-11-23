import subprocess
import csv
import os
import re
import time


os.environ["GOOGLE_CLOUD_PROJECT"] = "massive-gcp-473713"
TARGET_URL = "https://massive-gcp-473713.ew.r.appspot.com/api/timeline?user=user1"
OUTPUT_FILE = "out/fanout.csv"
POSTS_PER_USER = 100 
NB_USERS = 100  # 100 utilisateurs suffisent pour prouver le problème
FOLLOWERS_LIST = [10, 50, 100]
CONCURRENCY = 20   
TIMEOUT = 300      

def run_cmd(cmd):
    subprocess.run(cmd, shell=True, check=True)

def run():
    
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])

        total_posts = NB_USERS * POSTS_PER_USER 

        for followers in FOLLOWERS_LIST:
            print(f"\n==============================================")
            print(f" PARAMETRE FOLLOWERS: {followers} (Posts/User: {POSTS_PER_USER})")
            print(f"==============================================")

            # 1. CLEAN
            print("-> Nettoyage de la base")
            run_cmd("python3 clean.py")

            # 2. SEED
            print(f"-> Génération des données")
            run_cmd(f"python3 seed.py --users {NB_USERS} --posts {total_posts} --follows-min {followers} --follows-max {followers}")

            # 3. BENCHMARK
            print(f"-> Benchmark")
            
            for run_id in range(1, 4): 
                cmd = f"ab -k -c {CONCURRENCY} -n {CONCURRENCY*2} -t {TIMEOUT} \"{TARGET_URL}\""
                avg_time = "0ms"
                failed = 0
                
                try:
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    match = re.search(r"Time per request:\s+([0-9\.]+)\s+\[ms\]\s+\(mean\)", res.stdout)
                    
                    if match:
                        val = int(float(match.group(1)))
                        avg_time = f"{val}ms"
                    else:
                        failed = 1
                        print("[Erreur AB] Pas de temps trouvé.")

                    if "Non-2xx responses" in res.stdout or res.returncode != 0:
                        failed = 1
                        
                except Exception as e:
                    print(f"   [Exception] {e}")
                    failed = 1

                print(f"   Run {run_id}: {avg_time} | Failed: {failed}")
                writer.writerow([followers, avg_time, run_id, failed])
                f.flush()
                time.sleep(1)

    print(f"\n--- TERMINÉ ! ---")

if __name__ == '__main__':
    run()