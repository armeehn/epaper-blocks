#!/usr/bin/env python3
"""Validate every block descriptor against the rules a reviewer would check.

  python3 tools/validate_blocks.py [blocks/<id> ...]     (default: all)

Mirrors what the firmware enforces at install time (blocks.cpp), so a block
that passes here installs on a device. Exits non-zero on any error.
"""
import json, pathlib, re, sys
from urllib.parse import urlsplit

MAX_DESC = 4096          # BLK_MAX_DESC
MAX_PARAMS = 6           # BLK_MAX_PARAMS
MAX_EXTRACTS = 8         # BLK_MAX_EXTRACTS
MAX_ROWS = 6             # BlockData::rows
CATEGORIES = {"environment", "finance", "news", "developer", "calendar", "fun", "other"}
WIDGETS = {"big-number", "list", "text", "bar"}
PARAM_TYPES = {"string", "number", "choice"}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PRIVATE_HOST = re.compile(
    r"^(localhost|.*\.local|10\.|127\.|0\.|169\.254\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)")

# Field-length caps from BlockDef in firmware/epaper_dashboard/blocks.h. A
# longer value is silently truncated on the device, which is worse than a
# rejected PR.
CAPS = {"id": 27, "name": 31, "author": 27, "version": 9, "url": 199,
        "title": 27, "label": 27, "value": 19, "sub": 39, "list": 15,
        "param.key": 15, "param.label": 27, "param.default": 39, "param.choices": 95,
        "extract.name": 15, "extract.path": 63, "extract.prefix": 7,
        "extract.suffix": 11, "extract.map": 159,
        "extract.primary": 23, "extract.secondary": 23}


def check(block_dir: pathlib.Path, err):
    f = block_dir / "block.json"
    if not f.exists():
        return err(f"{block_dir}: no block.json")
    raw = f.read_bytes()
    if len(raw) > MAX_DESC:
        err(f"{f}: descriptor is {len(raw)} bytes (max {MAX_DESC})")
    try:
        b = json.loads(raw)
    except json.JSONDecodeError as e:
        return err(f"{f}: invalid JSON — {e}")

    def cap(field, value):
        if value is not None and len(str(value)) > CAPS[field]:
            err(f"{f}: {field} is {len(str(value))} chars, truncated on device at {CAPS[field]}")

    for k in ("id", "name", "author", "version", "description", "category",
              "source", "extract", "render"):
        if k not in b:
            err(f"{f}: missing required field '{k}'")
    if any(k not in b for k in ("id", "source", "render")):
        return

    if not ID_RE.match(b["id"]):
        err(f"{f}: id '{b['id']}' must be lowercase-kebab")
    if b["id"] != block_dir.name:
        err(f"{f}: id '{b['id']}' must equal the directory name '{block_dir.name}'")
    if b.get("category") not in CATEGORIES:
        err(f"{f}: category '{b.get('category')}' not one of {sorted(CATEGORIES)}")
    for k in ("id", "name", "author", "version"):
        cap(k, b.get(k))
    if not (block_dir / "README.md").exists():
        err(f"{block_dir}: add a README.md (what it shows, upstream API, terms)")

    src = b["source"]
    if src.get("type") not in ("json", "text"):
        err(f"{f}: source.type must be 'json' or 'text'")
    url = src.get("url", "")
    cap("url", url)
    parts = urlsplit(url)
    if parts.scheme != "https":
        err(f"{f}: source.url must be https:// (got '{parts.scheme or 'none'}')")
    if PRIVATE_HOST.match(parts.hostname or ""):
        err(f"{f}: source.url host '{parts.hostname}' is private/loopback/.local")
    # Placeholders must resolve to declared params, and vice versa.
    used = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", url))
    declared = {p.get("key") for p in b.get("params", [])}
    for u in used - declared:
        err(f"{f}: url uses {{{u}}} with no matching param")
    for d in declared - used:
        err(f"{f}: param '{d}' is never used in the url")

    params = b.get("params", [])
    if len(params) > MAX_PARAMS:
        err(f"{f}: {len(params)} params (max {MAX_PARAMS})")
    for p in params:
        if p.get("type", "string") == "secret":
            err(f"{f}: secret params are refused by the device")
        elif p.get("type", "string") not in PARAM_TYPES:
            err(f"{f}: param '{p.get('key')}' type must be one of {sorted(PARAM_TYPES)}")
        if p.get("type") == "choice" and not p.get("choices"):
            err(f"{f}: choice param '{p.get('key')}' needs 'choices'")
        for k in ("key", "label", "default", "choices"):
            cap(f"param.{k}", p.get(k))

    extracts = b.get("extract", [])
    if len(extracts) > MAX_EXTRACTS:
        err(f"{f}: {len(extracts)} extracts (max {MAX_EXTRACTS})")
    names = set()
    for x in extracts:
        if not x.get("name"):
            err(f"{f}: every extract needs a 'name'")
        # An empty path means "the response root itself", which is only
        # meaningful when the root is the array a list widget consumes.
        if not x.get("path") and not x.get("primary"):
            err(f"{f}: extract '{x.get('name')}' needs a 'path' "
                f"(empty path is only valid for a list over the response root)")
        names.add(x.get("name"))
        if x.get("limit", 0) > MAX_ROWS:
            err(f"{f}: extract '{x.get('name')}' limit {x['limit']} > {MAX_ROWS} rows shown")
        for k in ("name", "path", "prefix", "suffix", "map", "primary", "secondary"):
            cap(f"extract.{k}", x.get(k))

    r = b["render"]
    if r.get("widget") not in WIDGETS:
        err(f"{f}: render.widget must be one of {sorted(WIDGETS)}")
    for k in ("title", "label", "value", "sub", "list"):
        cap(k, r.get(k))
    if r.get("widget") == "list":
        if r.get("list") not in names:
            err(f"{f}: render.list '{r.get('list')}' is not an extract name")
    if r.get("widget") in ("big-number", "bar") and not r.get("value"):
        err(f"{f}: widget '{r['widget']}' needs render.value")
    # Every {binding} in value/sub/label must name an extract.
    for k in ("value", "sub", "label"):
        for ref in re.findall(r"\{([a-zA-Z0-9_]+)\}", str(r.get(k, ""))):
            if ref not in names:
                err(f"{f}: render.{k} references {{{ref}}}, not an extract name")
    for k in ("minW", "minH"):
        v = r.get(k)
        if v is not None and not (1 <= v <= (16 if k == "minW" else 12)):
            err(f"{f}: render.{k}={v} is outside the 16x12 grid")


def main(argv):
    dirs = [pathlib.Path(a) for a in argv[1:]] or sorted(
        d for d in pathlib.Path("blocks").iterdir() if d.is_dir())
    errors = []
    for d in dirs:
        check(d, errors.append)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    print(f"{len(dirs)} block(s) checked, {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
