# epaper-blocks

Community block registry for the [e-paper dashboard](https://github.com/armeehn/epaper-dashboard).

**A block is data, never code.** It is a ~20-line JSON file declaring an HTTPS
source, which values to pull out of the response, and which widget draws them.
The device ships a fixed interpreter for exactly that vocabulary — a block
cannot loop, compute, or execute. Reviewing a contribution means reading a URL
and a few paths, not auditing a program.

A registry is just **static files behind HTTPS**. This repository, served from
GitHub, is one; there is no server component.

## Install these blocks

In the dashboard's **Blocks** tab (or during first-run setup, in the **Store**
step), load:

```
https://raw.githubusercontent.com/armeehn/epaper-blocks/main/index.json
```

That URL is the built-in default, so normally you just press *Load*. The device
verifies the index signature before listing anything, and each block's own
signature before storing it.

## Catalogue

| Block | Category | Source | Key needed |
| --- | --- | --- | --- |
| Air quality | environment | Open-Meteo | no |
| UV index | environment | Open-Meteo | no |
| Sunrise & sunset | environment | sunrise-sunset.org | no |
| Crypto price | finance | CoinGecko | no |
| Crypto + 24 h change | finance | CoinGecko | no |
| FX rate | finance | Frankfurter (ECB data) | no |
| Stock price | finance | Yahoo Finance (unofficial) | no |
| GitHub stars | developer | GitHub REST | no |
| Hacker News | news | HN Algolia | no |
| Earthquakes | news | USGS | no |
| Space launches | news | Launch Library 2 | no |
| Upcoming holidays | calendar | Nager.Date | no |
| Quote of the day | fun | ZenQuotes | no |

Blocks may not declare secret parameters, so anything requiring an API token is
out of scope by design.

## Contribute a block

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and the review
checklist, and [BLOCK_SPEC.md](BLOCK_SPEC.md) for the field reference. In short:
add `blocks/<id>/block.json` plus a README, run `python3 tools/validate_blocks.py`,
and open a PR. On merge a maintainer re-signs and republishes the index.

CI additionally runs `pytest`, which re-verifies every published `.epb` and the
index against `keys/epaper-blocks.pub.pem` and checks that what the registry
publishes is what a device will accept.

## Run your own registry

Everything here is reproducible with your own key:

```sh
python3 tools/block_sign.py keygen my-registry     # keep my-registry.key offline
./rebuild.sh my-registry.key my-registry-2026 https://you.example/blocks
```

The keyid you pass is not decoration: a device matches it against
`trusted_keys.h` before it checks the signature, so it has to be the same string
in both places.

To make a device trust it, add `my-registry.pub.pem` to
`firmware/epaper_dashboard/trusted_keys.h` in the firmware repository and
reflash. Which registry you *browse* is a runtime setting; whose signature you
*trust* is compile-time. See [SECURITY.md](SECURITY.md).

## Licence

[MIT](LICENSE). Each block's upstream data source has its own terms — check the
block's README before relying on one.
