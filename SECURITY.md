# Security

## Trust model in one page

Two independent things, only one of which needs a reflash:

| | Where it lives | To change |
| --- | --- | --- |
| Which registry you install **from** | a URL in the Blocks tab | runtime, nothing to reflash |
| Whose signature the device **trusts** | `firmware/epaper_dashboard/trusted_keys.h` | recompile + reflash |

Blocks are `.epb` envelopes signed with ECDSA P-256 + SHA-256. A device verifies
the signature *before* parsing or storing anything, and the default policy is
signed-only; unsigned installs require an explicit opt-in intended for local
development.

## What a hostile block can and cannot do

- **Execute code** — impossible by construction. There is no interpreter for
  anything Turing-shaped; the descriptor selects from a fixed vocabulary.
- **Steal credentials** — blocks cannot declare secret params and have no access
  to IMAP/CalDAV settings. Nothing but a block's own params is substitutable
  into its URL.
- **Probe your LAN** — fetches must be `https://`; literal private, loopback and
  link-local addresses and `.local` hosts are refused. DNS rebinding is out of
  scope for v1; the fetch carries no credentials in any case.
- **Abuse resources** — descriptor ≤ 4 KB, ≤ 16 installed blocks, response
  ≤ 16 KB, one fetch per block per wake cycle, 10 s timeout.
- **Show something false** — yes. Signing is not taste; registry review is the
  curation layer, and the panel shows data, never actions.

## The registry key

This registry signs with keyid **`epaper-blocks-2026`**; the public half is
published as `keys/epaper-blocks.pub.pem` and is the trust anchor compiled into
stock firmware (`firmware/epaper_dashboard/trusted_keys.h`). The private half is
held offline by the maintainer and is in no clone of this repository, so nobody
else can produce a `.epb` that an unmodified device accepts.

The keyid is part of the contract, not a label. A device looks a signature up by
keyid *before* it verifies anything, so a registry signed with a key that is
cryptographically fine but carries an unrecognised keyid is rejected wholesale —
which is why `rebuild.sh` defaults to the published keyid and CI asserts it.

Anyone running a real registry must mint their own key
(`python3 tools/block_sign.py keygen my-registry`), keep the private half
offline, ship only the public half in the firmware's `trusted_keys.h`, and
remove the entry above. `.gitignore` excludes `*.key`, with no exception.

## Reporting a vulnerability

Report issues in the block engine, the signature verification, or the tooling in
this repository through
[GitHub security advisories](https://github.com/armeehn/epaper-blocks/security/advisories/new).
Please do not open a public issue for a signature-verification bypass.

For firmware issues, use the [firmware repository's](https://github.com/armeehn/epaper-dashboard/security/advisories/new)
advisory form instead.
