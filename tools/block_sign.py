#!/usr/bin/env python3
"""Block registry tooling: keygen, sign, verify, index.

  block_sign.py keygen <name>                 -> <name>.key (private) + <name>.pub.pem
  block_sign.py sign <key> <keyid> <block.json> [out.epb]
  block_sign.py verify <pub.pem> <file.epb>
  block_sign.py index <key> <keyid> <baseurl> <blockdir>...   -> index.json (signed)

Signatures: ECDSA P-256 + SHA-256 (DER), over the exact payload bytes.
Requires: pip install cryptography
"""
import sys, json, base64, pathlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.primitives import hashes, serialization

def load_priv(path):
    return serialization.load_pem_private_key(pathlib.Path(path).read_bytes(), password=None)

def sign_bytes(priv, data: bytes) -> bytes:
    digest = hashes.Hash(hashes.SHA256()); digest.update(data)
    return priv.sign(digest.finalize(), ec.ECDSA(Prehashed(hashes.SHA256())))

def make_epb(priv, keyid, payload: bytes) -> dict:
    return {
        "format": "epb1",
        "payload": base64.b64encode(payload).decode(),
        "sigs": [{"keyid": keyid, "alg": "ecdsa-p256-sha256",
                  "sig": base64.b64encode(sign_bytes(priv, payload)).decode()}],
    }

def cmd_keygen(name):
    priv = ec.generate_private_key(ec.SECP256R1())
    pathlib.Path(f"{name}.key").write_bytes(priv.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    pathlib.Path(f"{name}.pub.pem").write_bytes(priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    print(f"wrote {name}.key (KEEP PRIVATE) and {name}.pub.pem (goes into trusted_keys.h)")

def cmd_sign(key, keyid, block, out=None):
    payload = pathlib.Path(block).read_bytes()
    json.loads(payload)  # must be valid JSON
    epb = make_epb(load_priv(key), keyid, payload)
    out = out or str(pathlib.Path(block).with_suffix(".epb"))
    pathlib.Path(out).write_text(json.dumps(epb, indent=1))
    print(f"signed -> {out}")

def cmd_verify(pub, epbfile):
    epb = json.loads(pathlib.Path(epbfile).read_text())
    payload = base64.b64decode(epb["payload"])
    sig = base64.b64decode(epb["sigs"][0]["sig"])
    pubkey = serialization.load_pem_public_key(pathlib.Path(pub).read_bytes())
    digest = hashes.Hash(hashes.SHA256()); digest.update(payload)
    pubkey.verify(sig, digest.finalize(), ec.ECDSA(Prehashed(hashes.SHA256())))
    body = json.loads(payload)
    # a payload is either a single block descriptor or a registry index
    if body.get("format") == "epb-index1":
        what = f"index of {len(body.get('blocks', []))} blocks"
    else:
        what = body.get("id", "unknown block")
    print(f"OK: valid signature by keyid={epb['sigs'][0]['keyid']}, "
          f"payload {len(payload)} bytes ({what})")

def cmd_index(key, keyid, baseurl, *dirs):
    priv = load_priv(key)
    entries = []
    for d in dirs:
        d = pathlib.Path(d)
        block = json.loads((d / "block.json").read_text())
        render = block.get("render", {})
        entry = {
            "id": block["id"], "name": block.get("name", block["id"]),
            "author": block.get("author", "?"), "version": block.get("version", "0"),
            "description": block.get("description", ""),
            "category": block.get("category", "other"),
            "epb": f"{baseurl.rstrip('/')}/{d.name}/{d.name}.epb",
        }
        # Size hints let the store front show a tile at its true proportions
        # and let the layout editor place it without a round-trip.
        for k in ("minW", "minH"):
            if k in render:
                entry[k] = render[k]
        # Optional; the portal skips the image when it can't be fetched (the
        # setup hotspot has no route to the internet).
        if (d / "screenshot.png").exists():
            entry["screenshot"] = f"{baseurl.rstrip('/')}/{d.name}/screenshot.png"
        entries.append(entry)
    payload = json.dumps({"format": "epb-index1", "blocks": entries}, indent=1).encode()
    pathlib.Path("index.json").write_text(json.dumps(make_epb(priv, keyid, payload), indent=1))
    print(f"wrote signed index.json with {len(entries)} blocks")

if __name__ == "__main__":
    cmds = {"keygen": cmd_keygen, "sign": cmd_sign, "verify": cmd_verify, "index": cmd_index}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__); sys.exit(1)
    cmds[sys.argv[1]](*sys.argv[2:])
