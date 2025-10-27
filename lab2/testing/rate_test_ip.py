import threading
import time
import socket
from collections import Counter

# ------------------------------------------------------------------
# Helper: perform a single HTTP GET and return the status code
# ------------------------------------------------------------------
def fetch(host="127.0.0.1", port=8081, path="/drstone.png"):
    try:
        req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        with socket.create_connection((host, port), timeout=3) as s:
            s.sendall(req.encode())
            data = b""
            while chunk := s.recv(4096):
                data += chunk
        line = data.split(b"\r\n", 1)[0].decode(errors="ignore")
        parts = line.split()
        return parts[1] if len(parts) > 1 else "ERR"
    except Exception:
        return "ERR"

# ------------------------------------------------------------------
# Client logic (spam or polite)
# ------------------------------------------------------------------
def run_client(label, host, port, total, delay):
    results = []
    t0 = time.time()
    for _ in range(total):
        results.append(fetch(host, port))
        time.sleep(delay)
    elapsed = time.time() - t0
    counts = Counter(results)
    succ = counts["200"]
    denied = counts["429"]
    print(f"\n--- {label} ---")
    print(f"Requests: {total}, Delay: {delay}s → {1/delay:.1f} req/s attempt")
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"200 OK: {succ}, 429 Too Many: {denied}")
    print(f"Other: {dict(counts)}")
    return counts

# ------------------------------------------------------------------
# Run both clients concurrently to show per-IP awareness
# ------------------------------------------------------------------
def run_concurrent_test(host="127.0.0.1", port=8081):
    print("IP Awareness Test")


    spam_thread = threading.Thread(
        target=run_client, args=("Client A", host, port, 50, 0.05)
    )
    polite_thread = threading.Thread(
        target=run_client, args=("Client B", host, port, 50, 0.25)
    )

    t0 = time.time()
    spam_thread.start()
    time.sleep(0.1)
    polite_thread.start()
    spam_thread.join()
    polite_thread.join()
    t1 = time.time()

    print(f"\n=== Test complete in {t1 - t0:.2f}s ===")
    print("Expect many 429s for the spammer and mostly 200 OK for the polite client.\n")

# ------------------------------------------------------------------
if __name__ == "__main__":
    run_concurrent_test()
