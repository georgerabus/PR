# server_single.py
import os, sys, socket, urllib.parse, mimetypes, time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# --- Settings from command line ---
if len(sys.argv) < 2:
    print("Usage: python server_single.py <directory> [--port PORT]")
    sys.exit(1)

root = Path(sys.argv[1]).resolve()
port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8080
mime_whitelist = {"text/html", "image/png", "application/pdf"}

# --- Request counter (NAIVE: no locking needed yet, we're single-threaded) ---
hit_count = defaultdict(int)

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

def listing(path):
    # build a table like the screenshot, including hit counts
    rel = str(path.relative_to(root)) if path != root else "/"
    rows = []
    for entry in sorted(path.iterdir()):
        name = entry.name + ("/" if entry.is_dir() else "")
        href = urllib.parse.quote(name)
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

# --- Server loop (single-threaded) ---
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(("0.0.0.0", port))
    s.listen(1)
    print(f"[single] Serving {root} on port {port}", flush=True)
    while True:
        conn, addr = s.accept()
        with conn:
            req = conn.recv(1024).decode(errors="ignore")
            if not req:
                continue
            line = req.split("\r\n")[0]
            parts = line.split()
            if len(parts) < 2:
                conn.sendall(response("400 Bad Request", "<h1>400 Bad Request</h1>"))
                log(addr, "?", "?", "400 Bad Request")
                continue

            method, raw_path = parts[0], parts[1]
            path = urllib.parse.unquote(raw_path)

            # artificial work delay (~1s) for benchmarking
            time.sleep(1.0)

            if method not in ("GET", "HEAD"):
                conn.sendall(response("405 Method Not Allowed", "<h1>405</h1>"))
                log(addr, method, path, "405 Method Not Allowed")
                continue

            fs_path = (root / path.lstrip("/")).resolve()
            if not str(fs_path).startswith(str(root)):
                conn.sendall(not_found())
                log(addr, method, path, "404 Not Found")
                continue

            # count hits (safe because single-threaded)
            hit_count[str(fs_path)] += 1

            if fs_path.is_dir():
                conn.sendall(listing(fs_path))
                log(addr, method, path, "200 OK (directory)")
            elif fs_path.is_file():
                ctype = mimetypes.guess_type(fs_path.name)[0] or "application/octet-stream"
                if ctype not in mime_whitelist:
                    conn.sendall(not_found())
                    log(addr, method, path, "404 Not Found (unsupported type)")
                    continue
                with open(fs_path, "rb") as f:
                    data = f.read()
                conn.sendall(response("200 OK", b"" if method == "HEAD" else data, ctype))
                log(addr, method, path, "200 OK")
            else:
                conn.sendall(not_found())
                log(addr, method, path, "404 Not Found")
