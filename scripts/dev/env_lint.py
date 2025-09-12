from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple


REQUIRED_KEYS: Tuple[str, ...] = (
    "ICE_API_TOKEN",
    "DATABASE_URL",
    "ALEMBIC_SYNC_URL",
    "REDIS_URL",
)


def parse_env(path: Path) -> List[Tuple[str, str]]:
    lines = []
    for raw in path.read_text().splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        lines.append((k.strip(), v))
    return lines


def lint_env(path: Path) -> int:
    problems: List[str] = []
    kvs = parse_env(path)

    # Duplicate keys
    seen: Dict[str, int] = {}
    for k, _ in kvs:
        seen[k] = seen.get(k, 0) + 1
    dups = [k for k, c in seen.items() if c > 1]
    if dups:
        problems.append(f"duplicate keys: {', '.join(sorted(dups))}")

    # Required keys
    present = {k for k, _ in kvs}
    missing = [k for k in REQUIRED_KEYS if k not in present]
    if missing:
        problems.append(f"missing required keys: {', '.join(missing)}")

    # Values sanity
    valmap = {k: v for k, v in kvs}
    if valmap.get("ICE_API_TOKEN") in (None, "", "dev-token", "REPLACE_ME_STRONG_RANDOM_TOKEN"):
        problems.append("ICE_API_TOKEN must be a strong non-default value")

    db = valmap.get("DATABASE_URL", "")
    if "+asyncpg://" not in db or "sslmode=require" not in db:
        problems.append("DATABASE_URL must use postgresql+asyncpg and sslmode=require for prod")

    ale = valmap.get("ALEMBIC_SYNC_URL", "")
    if ale.startswith("postgresql+asyncpg://"):
        problems.append("ALEMBIC_SYNC_URL must use postgresql:// (sync driver), not +asyncpg")
    if "sslmode=require" not in ale:
        problems.append("ALEMBIC_SYNC_URL must include sslmode=require for prod")

    if problems:
        sys.stderr.write("env-lint errors in %s\n" % path)
        for p in problems:
            sys.stderr.write(f" - {p}\n")
        return 1
    print("env-lint: OK")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Lint a .env file for duplicates and required keys")
    ap.add_argument("env_path", nargs="?", default=".env.prod")
    args = ap.parse_args()
    code = lint_env(Path(args.env_path))
    sys.exit(code)


if __name__ == "__main__":
    main()


