import threading, time, socket, statistics

def fetch(host="127.0.0.1", port=8081, path="/", results=None, index=None):
    try:
        req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        with socket.create_connection((host, port), timeout=3) as s:
            s.sendall(req.encode())
            data = b""
            while chunk := s.recv(4096):
                data += chunk
        status = data.split(b"\r\n", 1)[0].decode(errors="ignore").split()
        code = status[1] if len(status) > 1 else "ERR"
    except Exception as e:
        code = f"ERR({e})"
    if results is not None and index is not None:
        results[index] = code
    return code

def spam_test(host="127.0.0.1", port=8081, total=50, delay=0.05):
    results = [None] * total
    t0 = time.time()
    threads = []
    for i in range(total):
        th = threading.Thread(target=fetch, args=(host, port, "/", results, i))
        th.start()
        threads.append(th)
        time.sleep(delay)  # controls request rate
    for th in threads:
        th.join()
    t1 = time.time()

    elapsed = t1 - t0
    count_200 = results.count("200")
    count_429 = results.count("429")
    total_rps = total / elapsed
    succ_rps = count_200 / elapsed
    denied_rps = count_429 / elapsed

    print(f"\n{total} requests, delay={delay}s")
    print(f"time: {elapsed:.2f}s ({total_rps:.1f} total requests/seconds)")
    print(f"200 : {count_200}  ({succ_rps:.1f} requests/seconds)")
    print(f"429 : {count_429}  ({denied_rps:.1f} requests/seconds)")
    return results

# ------------------------------------------------------------
# Run both tests
# ------------------------------------------------------------
if __name__ == "__main__":
    print("Testing rate limiting on threaded server (port 8081)...")
    spam_results = spam_test("127.0.0.1", 8081, total=50, delay=0.05)
    polite_results = spam_test("127.0.0.1", 8081, total=50, delay=0.25)
