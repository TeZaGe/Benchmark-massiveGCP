import subprocess
import csv
import re
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
BASE_URL = "https://massive-gcp-473713.ew.r.appspot.com/api/timeline"
OUTPUT_FILE = "out/conc.csv"
PARAMS = [1, 10, 20, 50, 100, 1000]


def run(num_users: int):
    """Run concurrence tests: for each c in PARAMS launch min(c, num_users)
    ab instances in parallel (each does a single request). This makes the
    total concurrent requests equal to c when enough users are available.
    """
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PARAM", "AVG_TIME", "RUN", "FAILED"])
        print_lock = threading.Lock()

        for concurrency in PARAMS:
            c = concurrency
            target_count = min(c, num_users)
            if target_count < c:
                with print_lock:
                    print(f"[WARN] --users={num_users} < requested concurrency {c}. "
                          f"Seuls {target_count} users seront lancés (parallélisme total = {target_count}).")

            with print_lock:
                print(f"\n--- Test Concurrence: {c} (instances simultanées: {target_count}) ---")

            for run_id in range(1, 4):
                with print_lock:
                    print(f"  Run {run_id}/3 pour concurrency={c}")

                def ab_one(user_idx: int):
                    target_url = f"{BASE_URL}?user=user{user_idx}"
                    cmd = f"ab -k -c 1 -n 1 -t 5 \"{target_url}\""
                    try:
                        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        output = (res.stdout or "") + "\n" + (res.stderr or "")
                        match = re.search(r"Time per request:\s+([0-9\.]+)\s+\[ms\]\s+\(mean\)", output)
                        if match:
                            return (int(float(match.group(1))), 0)
                        else:
                            with print_lock:
                                print(f"[ab failed] cmd={cmd}\noutput=\n{output}")
                            return (0, 1)
                    except Exception as e:
                        with print_lock:
                            print(f"Erreur instance user{user_idx}: {e}")
                        return (0, 1)

                times = []
                failed = 0

                if target_count == 0:
                    with print_lock:
                        print("Aucun user disponible pour ce niveau de concurrence, on passe.")
                    writer.writerow([c, "0ms", run_id, target_count])
                    continue

                with ThreadPoolExecutor(max_workers=target_count) as ex:
                    futures = {ex.submit(ab_one, uid): uid for uid in range(1, target_count + 1)}
                    for fut in as_completed(futures):
                        t, err = fut.result()
                        if err:
                            failed += 1
                        else:
                            times.append(t)

                avg_time = f"{int(sum(times)/len(times))}ms" if times else "0ms"
                with print_lock:
                    if failed > 1 :
                        failed = 1
                    print(f"   Run {run_id}: {avg_time} | Failed: {failed}")
                writer.writerow([c, avg_time, run_id, failed])
                f.flush()
                time.sleep(1)


def parse_args():
    p = argparse.ArgumentParser(description='Bench concurrence (ab) for multiple users')
    p.add_argument('-u', '--users', type=int, default=None, help='Nombre d\'utilisateurs disponibles (user1..userN). Par défaut = max(PARAMS)')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    users = args.users if args.users is not None else max(PARAMS)
    if users < 1:
        print("Le nombre d'utilisateurs doit être >= 1")
    else:
        run(users)