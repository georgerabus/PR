# server_threaded.py
import os, sys, socket, urllib.parse, mimetypes, time, threading, collections
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque

# --- Settings from command line ---
if len(sys.argv) < 2:
    print("Usage: python server_threaded.py <directory> [--port PORT]")
    sys.exit(1)

root = Path(sys.argv[1]).resolve()
port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8080
mime_whitelist = {"text/html", "image/png", "application/pdf"}

# --- Shared state (must be protected!) ---
hit_count = defaultdict(int)         # path -> int
hit_lock = threading.Lock()

# rate limiting: ip -> deque[timestamps_of_requests]
rate_window_sec = 1.0
rate_limit = 10
rate_lock = threading.Lock()
ip_requests = defaultdict(lambda: deque())

def too_many_requests(ip):
    """
    Returns True if this request should be rejected (429),
    and records this attempt if allowed.
    """
    now = time.time()
    with rate_lock:
        dq = ip_requests[ip]
        # drop old timestamps
        while dq and now - dq[0] > rate_window_sec:
            dq.popleft()

        if len(dq) >= rate_limit:
            # already at or above limit
            return True

        # record this request
        dq.append(now)
        return False

# --- Helpers ---
def response(status, body="", ctype="text/html"):
    body_bytes = body.encode() if isinstance(body, str) else body
    headers = [
        f"HTTP/1.1 {status}",
        f"Date: {datetime.utcnow():%a, %d %b %Y %H:%M:%S GMT}",
        f"Content-Type: {ctype}",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close",
        "", "",
    ]
    return "\r\n".join(headers).encode() + body_bytes

def not_found():
    return response("404 Not Found", "<h1>404 Not Found</h1>")

def too_many():
    return response("429 Too Many Requests", "<h1>429 Too Many Requests</h1>")

def listing(path):
    rel = str(path.relative_to(root)) if path != root else "/"
    rows = []
    for entry in sorted(path.iterdir()):
        name = entry.name + ("/" if entry.is_dir() else "")
        href = urllib.parse.quote(name)
        with hit_lock:
            count = hit_count[str(entry.resolve())]
        rows.append(
            f'<tr><td><a href="{href}">{name}</a></td><td>{count}</td></tr>'
        )

    html = (
        "<html><head><title>Directory listing</title></head><body>"
        f"<h1>Directory listing for {rel}</h1>"
        '<table border="1" cellpadding="4" cellspacing="0">'
        "<tr><th>File / Directory</th><th>Hits</th></tr>"
        + "\n".join(rows) +
        "</table></body></html>"
    )
    return response("200 OK", html)

def log(addr, method, path, status):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {addr[0]} {method} {path} {status}", flush=True)

def handle_client(conn, addr):
    with conn:
        req = conn.recv(1024).decode(errors="ignore")
        if not req:
            return
        line = req.split("\r\n")[0]
        parts = line.split()
        if len(parts) < 2:
            conn.sendall(response("400 Bad Request", "<h1>400 Bad Request</h1>"))
            log(addr, "?", "?", "400 Bad Request")
            return

        method, raw_path = parts[0], parts[1]
        path = urllib.parse.unquote(raw_path)

        # rate limit check
        if too_many_requests(addr[0]):
            conn.sendall(too_many())
            log(addr, method, path, "429 Too Many Requests")
            return

        # artificial work delay (~1s)
        time.sleep(1.0)

        if method not in ("GET", "HEAD"):
            conn.sendall(response("405 Method Not Allowed", "<h1>405</h1>"))
            log(addr, method, path, "405 Method Not Allowed")
            return

        fs_path = (root / path.lstrip("/")).resolve()
        if not str(fs_path).startswith(str(root)):
            conn.sendall(not_found())
            log(addr, method, path, "404 Not Found")
            return

        # increment hit counter with lock (thread-safe)
        with hit_lock:
            hit_count[str(fs_path)] += 1

        if fs_path.is_dir():
            conn.sendall(listing(fs_path))
            log(addr, method, path, "200 OK (directory)")
        elif fs_path.is_file():
            ctype = mimetypes.guess_type(fs_path.name)[0] or "application/octet-stream"
            if ctype not in mime_whitelist:
                conn.sendall(not_found())
                log(addr, method, path, "404 Not Found (unsupported type)")
                return
            with open(fs_path, "rb") as f:
                data = f.read()
            conn.sendall(response("200 OK", b"" if method == "HEAD" else data, ctype))
            log(addr, method, path, "200 OK")
        else:
            conn.sendall(not_found())
            log(addr, method, path, "404 Not Found")

# --- Listener thread that spawns worker threads ---
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(("0.0.0.0", port))
    s.listen(50)  # higher backlog since we're concurrent
    print(f"[threaded] Serving {root} on port {port}", flush=True)
    while True:
        conn, addr = s.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()
