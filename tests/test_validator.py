"""Negative tests for tools/validate_blocks.py.

The validator's promise is in its own docstring: "a block that passes here
installs on a device". Each case below is a descriptor that used to pass review
here and then behaved badly on the device -- either refused at install time or,
worse, installed and silently rendered nothing.
"""
import json

import pytest

from conftest import validate_blocks as vb


def good():
    return {
        "id": "sample-block",
        "name": "Sample",
        "author": "tests",
        "version": "1.0",
        "description": "a descriptor used as a starting point",
        "category": "other",
        "source": {"type": "json", "url": "https://api.example.com/v1?q={q}"},
        "params": [{"key": "q", "label": "Q", "type": "string", "default": "a"}],
        "extract": [{"name": "v", "path": "a.b"}],
        "render": {"widget": "big-number", "title": "T", "value": "{v}"},
    }


def errors(tmp_path, block):
    d = tmp_path / block["id"]
    d.mkdir()
    (d / "block.json").write_text(json.dumps(block, indent=1))
    (d / "README.md").write_text("# test block\n")
    out = []
    vb.check(d, out.append)
    return out


def test_the_starting_point_is_clean(tmp_path):
    assert errors(tmp_path, good()) == []


# --- id length ------------------------------------------------------------
def test_id_at_the_device_limit_is_accepted(tmp_path):
    b = good()
    b["id"] = "a" * vb.MAX_ID
    assert errors(tmp_path, b) == []


def test_id_one_char_over_the_device_limit_is_refused(tmp_path):
    """char id[28] holds 27 chars, but blocks.cpp idOk() rejects >26.

    The cap table was sized from the struct field and allowed 27, so a 27-char
    id passed review here and then failed to install with the unhelpful
    "id must be short lowercase-kebab".
    """
    b = good()
    b["id"] = "a" * (vb.MAX_ID + 1)
    errs = errors(tmp_path, b)
    assert any("refuses any id longer" in e for e in errs), errs


# --- placeholders ---------------------------------------------------------
def test_placeholder_in_the_url_host_is_refused(tmp_path):
    """fsstore.cpp blockInstall(): "params are not allowed in the URL host"."""
    b = good()
    b["source"]["url"] = "https://{host}.example.com/v1?q={q}"
    b["params"].append({"key": "host", "label": "Host", "default": "api"})
    errs = errors(tmp_path, b)
    assert any("must not put a {param} in the host" in e for e in errs), errs


def test_unknown_placeholder_in_an_extract_path_is_refused(tmp_path):
    """blockFetch() substitutes params into paths; a typo renders "--" silently."""
    b = good()
    b["extract"] = [{"name": "v", "path": "{coyn}.usd"}]
    errs = errors(tmp_path, b)
    assert any("extract path uses {coyn}" in e for e in errs), errs


def test_declared_placeholder_in_an_extract_path_is_accepted(tmp_path):
    b = good()
    b["extract"] = [{"name": "v", "path": "{q}.usd"}]
    assert errors(tmp_path, b) == []


def test_param_used_only_in_a_path_counts_as_used(tmp_path):
    b = good()
    b["source"]["url"] = "https://api.example.com/v1"
    b["extract"] = [{"name": "v", "path": "{q}.usd"}]
    assert errors(tmp_path, b) == []


# --- extract / render pairing --------------------------------------------
def test_duplicate_extract_names_are_refused(tmp_path):
    b = good()
    b["extract"] = [{"name": "v", "path": "a"}, {"name": "v", "path": "b"}]
    errs = errors(tmp_path, b)
    assert any("duplicate extract name" in e for e in errs), errs


def test_list_widget_fed_by_a_scalar_extract_is_refused(tmp_path):
    """BW_LIST reads rows[], which only an extract with 'primary' ever fills."""
    b = good()
    b["extract"] = [{"name": "rows", "path": "items"}]
    b["render"] = {"widget": "list", "title": "T", "list": "rows"}
    errs = errors(tmp_path, b)
    assert any("names a scalar extract" in e for e in errs), errs


def test_list_widget_fed_by_a_list_extract_is_accepted(tmp_path):
    b = good()
    b["extract"] = [{"name": "rows", "path": "items", "primary": "title", "limit": 4}]
    b["render"] = {"widget": "list", "title": "T", "list": "rows"}
    assert errors(tmp_path, b) == []


def test_list_rows_a_widget_never_draws_are_refused(tmp_path):
    b = good()
    b["extract"] = [{"name": "rows", "path": "items", "primary": "title"}]
    b["render"] = {"widget": "text", "title": "T", "sub": "hello"}
    errs = errors(tmp_path, b)
    assert any("never draws them" in e for e in errs), errs


# --- rules that already held, kept as a regression floor ------------------
def test_secret_param_is_refused(tmp_path):
    b = good()
    b["params"] = [{"key": "q", "label": "Q", "type": "secret"}]
    errs = errors(tmp_path, b)
    assert any("secret params" in e for e in errs), errs


def test_plain_http_is_refused(tmp_path):
    b = good()
    b["source"]["url"] = "http://api.example.com/v1?q={q}"
    errs = errors(tmp_path, b)
    assert any("must be https" in e for e in errs), errs


@pytest.mark.parametrize("host", ["10.0.0.5", "192.168.1.4", "127.0.0.1",
                                  "169.254.1.1", "172.20.0.1", "printer.local"])
def test_private_and_local_hosts_are_refused(tmp_path, host):
    b = good()
    b["source"]["url"] = f"https://{host}/v1?q={{q}}"
    errs = errors(tmp_path, b)
    assert any("private/loopback/.local" in e for e in errs), errs


def test_oversized_descriptor_is_refused(tmp_path):
    b = good()
    b["description"] = "x" * (vb.MAX_DESC + 1)
    errs = errors(tmp_path, b)
    assert any("descriptor is" in e for e in errs), errs


def test_render_binding_with_no_extract_is_refused(tmp_path):
    b = good()
    b["render"]["value"] = "{nope}"
    errs = errors(tmp_path, b)
    assert any("not an extract name" in e for e in errs), errs
