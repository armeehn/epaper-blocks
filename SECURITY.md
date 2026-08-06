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

## The demo key

`keys/demo-registry.key` is a **demo key whose private half is public**, kept so
the examples install out of the box on an unmodified build. It is not a trust
anchor: anyone can sign a block a stock device accepts until it is replaced.

Anyone running a real registry must generate their own key, keep the private
half offline, ship only the public half in the firmware's `trusted_keys.h`, and
delete the demo entry. `.gitignore` excludes `*.key` apart from that one
documented file.

## Reporting a vulnerability

Report issues in the block engine, the signature verification, or the tooling in
this repository through
[GitHub security advisories](https://github.com/armeehn/epaper-blocks/security/advisories/new).
Please do not open a public issue for a signature-verification bypass.

For firmware issues, use the [firmware repository's](https://github.com/armeehn/epaper-dashboard/security/advisories/new)
advisory form instead.
