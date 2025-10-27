import threading
import time
import socket

def fetch(host, port, path="/", results=None, index=None):
    try:
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )

        with socket.create_connection((host, port)) as s:
            s.sendall(req.encode())

            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk

        # split headers/body
        sep = data.find(b"\r\n\r\n")
        if sep == -1:
            results[index] = "ERR(no headers)"
            return

        headers = data[:sep].decode(errors="ignore")
        status_line = headers.split("\r\n", 1)[0]
        parts = status_line.split()

        if len(parts) >= 2 and parts[1].isdigit():
            results[index] = parts[1]  # e.g. "200", "429"
        else:
            results[index] = "ERR(bad status)"
    except Exception as e:
        results[index] = f"ERR({e})"


def run_batch(label, host, port, path="/", n=10):
    results = [None] * n
    threads = []

    t0 = time.time()
    for i in range(n):
        th = threading.Thread(
            target=fetch,
            args=(host, port, path, results, i),
            daemon=True,
        )
        th.start()
        threads.append(th)

    for th in threads:
        th.join()
    t1 = time.time()

    total_time = t1 - t0

    # Print detailed per-request results
    for idx, status in enumerate(results):
        print(f"Request {idx:02d}: {status}")

    print(f"Total time for {n} concurrent requests: {total_time:.2f}s")

    return total_time, results


if __name__ == "__main__":
    path = "/"
    n = 10

    # Single-threaded server container
    run_batch(
        label="single-threaded",
        host="single",
        port=8080,
        path=path,
        n=n,
    )

    # Multithreaded server container
    run_batch(
        label="multithreaded",
        host="threaded",
        port=8081,
        path=path,
        n=n,
    )
