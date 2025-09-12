#!/usr/bin/env python3
import os, socket, sys
from urllib.parse import urlparse

TARGET_VARS = ("DATABASE_URL", "ALEMBIC_SYNC_URL", "SUPABASE_DB_URL")

def normalize(url: str):
    # tolerate async driver prefixes, leave query intact
    return url.replace("+asyncpg", "")

def probe(name: str, raw: str) -> bool:
    u = urlparse(normalize(raw))
    host, port = u.hostname, (u.port or 5432)
    print(f"[netcheck] resolve {name} → {host}:{port}")

    ok_any = False
    # getaddrinfo yields (family, socktype, proto, canonname, sockaddr)
    try:
        infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    except Exception as e:
        print(f"[netcheck] getaddrinfo failed for {host}:{port} :: {e}")
        return False
    for fam, st, proto, _, sa in infos:
        addr = sa[0]
        fam_name = "IPv4" if fam == socket.AF_INET else ("IPv6" if fam == socket.AF_INET6 else str(fam))
        s = socket.socket(fam, socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            s.connect(sa)
            s.close()
            print(f"[netcheck] TCP OK ({fam_name}) → {addr}:{port}")
            ok_any = True
            break
        except Exception as e:
            print(f"[netcheck] TCP FAIL ({fam_name}) → {addr}:{port} :: {e}")
            try:
                s.close()
            except Exception:
                pass
    return ok_any

print("[netcheck] /etc/resolv.conf:")
try:
    print(open("/etc/resolv.conf").read().strip())
except Exception as e:
    print("  <cannot read resolv.conf>", e)

all_ok = True
for var in TARGET_VARS:
    raw = os.environ.get(var, "")
    if not raw:
        print(f"[netcheck] {var} missing"); all_ok = False; continue
    if not probe(var, raw):
        all_ok = False

sys.exit(0 if all_ok else 12)
