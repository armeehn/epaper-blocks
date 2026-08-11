"""The seam between this registry and the firmware that installs from it.

Every test here answers one question: is a block that passes review in this
repository actually installable on a stock device?  That has three independent
parts -- the bytes we publish, the signature over them, and the *keyid* the
device looks that signature up by -- and getting two of the three right still
produces a registry no device will touch.

    pip install cryptography pytest && pytest -q
"""
import base64
import json
import pathlib
import re
import subprocess
import sys

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.exceptions import InvalidSignature

from conftest import ROOT, validate_blocks

BLOCK_DIRS = sorted(d for d in (ROOT / "blocks").iterdir() if d.is_dir())
IDS = [d.name for d in BLOCK_DIRS]
PUBKEY = ROOT / "keys" / "epaper-blocks.pub.pem"

# --- constants that belong to the firmware, restated here on purpose --------
# Changing one of these without changing the other side is exactly the class of
# break these tests exist to catch, so they are written as literals with the
# firmware symbol named, not derived from anything in this repository.
KEYID = "epaper-blocks-2026"          # trusted_keys.h  TRUSTED_KEYS[0].keyid
ALG = "ecdsa-p256-sha256"             # blocksig.cpp    epbOpen()
REGISTRY_MAX_BYTES = 24576            # config.h        REGISTRY_MAX_BYTES
BLK_MAX_DESC = 4096                   # blocks.h        BLK_MAX_DESC


def load_pub():
    return serialization.load_pem_public_key(PUBKEY.read_bytes())


def verify(payload: bytes, sig: bytes) -> None:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(payload)
    load_pub().verify(sig, digest.finalize(), ec.ECDSA(Prehashed(hashes.SHA256())))


def envelope(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


@pytest.fixture(scope="session")
def index():
    return envelope(ROOT / "index.json")


@pytest.fixture(scope="session")
def index_payload(index):
    return json.loads(base64.b64decode(index["payload"]))


# --------------------------------------------------------------------------
# every descriptor passes the reviewer-facing validator
# --------------------------------------------------------------------------
@pytest.mark.parametrize("d", BLOCK_DIRS, ids=IDS)
def test_block_descriptor_validates(d):
    errs = []
    validate_blocks.check(d, errs.append)
    assert errs == []


@pytest.mark.parametrize("d", BLOCK_DIRS, ids=IDS)
def test_descriptor_fits_the_device_cap(d):
    size = (d / "block.json").stat().st_size
    assert size <= BLK_MAX_DESC, f"{d.name} is {size} bytes (BLK_MAX_DESC {BLK_MAX_DESC})"


# --------------------------------------------------------------------------
# the published artefact is the reviewed source, signed by the right key,
# under the keyid a device can find
# --------------------------------------------------------------------------
@pytest.mark.parametrize("d", BLOCK_DIRS, ids=IDS)
def test_epb_payload_is_the_reviewed_block_json(d):
    payload = base64.b64decode(envelope(d / f"{d.name}.epb")["payload"])
    assert payload == (d / "block.json").read_bytes(), \
        f"{d.name}.epb has drifted from block.json — re-run ./rebuild.sh"


@pytest.mark.parametrize("d", BLOCK_DIRS, ids=IDS)
def test_epb_signature_verifies(d):
    env = envelope(d / f"{d.name}.epb")
    assert env["format"] == "epb1"
    payload = base64.b64decode(env["payload"])
    verify(payload, base64.b64decode(env["sigs"][0]["sig"]))


@pytest.mark.parametrize("d", BLOCK_DIRS, ids=IDS)
def test_epb_carries_the_keyid_the_firmware_trusts(d):
    """blocksig.cpp resolves keyid -> PEM *before* verifying anything.

    A signature made with the right private key but labelled with a keyid no
    device knows fails with "unknown signing key" and never reaches mbedTLS.
    Verifying against a PEM, as CI used to do alone, cannot see that.
    """
    sig = envelope(d / f"{d.name}.epb")["sigs"][0]
    assert sig["keyid"] == KEYID
    assert sig["alg"] == ALG


def test_index_signature_and_keyid(index):
    assert index["format"] == "epb1"
    assert index["sigs"][0]["keyid"] == KEYID
    assert index["sigs"][0]["alg"] == ALG
    verify(base64.b64decode(index["payload"]), base64.b64decode(index["sigs"][0]["sig"]))


def test_tampered_payload_fails_verification(index):
    payload = bytearray(base64.b64decode(index["payload"]))
    payload[10] ^= 0x01
    with pytest.raises(InvalidSignature):
        verify(bytes(payload), base64.b64decode(index["sigs"][0]["sig"]))


# --------------------------------------------------------------------------
# the index is what the store front actually reads
# --------------------------------------------------------------------------
def test_index_is_an_epb_index1(index_payload):
    assert index_payload["format"] == "epb-index1"


def test_index_fits_the_device_fetch_cap():
    size = (ROOT / "index.json").stat().st_size
    assert size <= REGISTRY_MAX_BYTES, \
        f"index.json is {size} bytes; the portal refuses more than {REGISTRY_MAX_BYTES}"


def test_index_lists_exactly_the_published_blocks(index_payload):
    assert sorted(e["id"] for e in index_payload["blocks"]) == IDS, \
        "index.json is stale — re-run ./rebuild.sh"


@pytest.mark.parametrize("d", BLOCK_DIRS, ids=IDS)
def test_index_entry_matches_its_descriptor(d, index_payload):
    entry = next(e for e in index_payload["blocks"] if e["id"] == d.name)
    block = json.loads((d / "block.json").read_text())
    for k in ("name", "author", "version", "description", "category"):
        assert entry[k] == block[k], f"{d.name}: index {k} differs from block.json"
    # Size hints drive the store tile and the layout editor's first placement.
    for k in ("minW", "minH"):
        assert entry.get(k) == block["render"].get(k), f"{d.name}: index {k} differs"


@pytest.mark.parametrize("d", BLOCK_DIRS, ids=IDS)
def test_index_epb_url_points_at_the_published_file(d, index_payload):
    entry = next(e for e in index_payload["blocks"] if e["id"] == d.name)
    # CONTRIBUTING: each entry is published as <baseurl>/<id>/<id>.epb.
    assert entry["epb"].endswith(f"/{d.name}/{d.name}.epb")
    assert entry["epb"].startswith("https://")
    if "screenshot" in entry:
        assert (d / "screenshot.png").exists()


# --------------------------------------------------------------------------
# tooling defaults are part of the contract too
# --------------------------------------------------------------------------
def test_rebuild_defaults_to_the_keyid_devices_trust():
    """A wrong default here publishes a registry that verifies and is rejected.

    ./rebuild.sh took its keyid from a default, so a maintainer running it the
    documented way would stamp every block with whatever that default said.
    """
    sh = (ROOT / "rebuild.sh").read_text()
    keyid = re.search(r'^KEYID=\$\{2:-(.+?)\}$', sh, re.M)
    assert keyid, "rebuild.sh no longer has a KEYID default"
    assert keyid.group(1) == KEYID


def test_rebuild_default_key_is_the_counterpart_of_the_published_pubkey():
    sh = (ROOT / "rebuild.sh").read_text()
    key = re.search(r'^KEY=\$\{1:-(.+?)\}$', sh, re.M)
    assert key, "rebuild.sh no longer has a KEY default"
    # The private half is offline and must never be committed, but the default
    # path has to name it, not some other key that was renamed away.
    assert key.group(1) == f"keys/{PUBKEY.name.replace('.pub.pem', '.key')}"


def test_no_private_key_is_committed():
    keys = [p for p in ROOT.rglob("*.key") if ".git/" not in str(p)]
    assert keys == [], f"private key material in a public repo: {keys}"


def test_documented_verify_command_works():
    """keys/README.md tells people to run exactly this; it has to run."""
    out = subprocess.run(
        [sys.executable, "tools/block_sign.py", "verify",
         "keys/epaper-blocks.pub.pem", "index.json"],
        cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert f"keyid={KEYID}" in out.stdout
