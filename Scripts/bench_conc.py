import subprocess
import csv
import re
import time

# --- CONFIGURATION ---
TARGET_URL = "https://massive-gcp-473713.ew.r.appspot.com/timeline/user1" 
OUTPUT_FILE = "out/conc.csv"
PARAMS = [1, 10, 20, 50, 100, 1000] 

def run():
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])

        for concurrency in PARAMS:
            # Pour la concurrence, on teste le paramètre c
            c = concurrency
            # On adapte le nombre de requêtes (n) pour qu'il soit au moins égal à c
            n = c if c >= 20 else 20 
            
            print(f"\n--- Test Concurrence: {c} (Requêtes: {n}) ---")

            for run_id in range(1, 4): 
                cmd = f"ab -k -c {c} -n {n} -t 5 {TARGET_URL}"
                
                avg_time = "0ms"
                failed = 0
                
                try:
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    output = res.stdout
                    
                    match = re.search(r"Time per request:\s+([0-9\.]+)\s+\[ms\]\s+\(mean\)", output)
                    if match:
                        avg_time = f"{int(float(match.group(1)))}ms"
                    else:
                        failed = 1
                    
                    if "Non-2xx responses" in output or res.returncode != 0:
                        failed = 1
                        
                except Exception as e:
                    print(f"Erreur: {e}")
                    failed = 1
                
                print(f"   Run {run_id}: {avg_time} | Failed: {failed}")
                writer.writerow([c, avg_time, run_id, failed])
                f.flush() 
                time.sleep(1) 

if __name__ == '__main__':
    run()