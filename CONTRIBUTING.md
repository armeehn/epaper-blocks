# Contributing a block

## Workflow

1. Create `blocks/<your-block-id>/block.json`. The **directory name must equal
   the `id`** — the index publishes each entry as `<baseurl>/<id>/<id>.epb`.
   Copy an existing block as a starting point; fields are documented in
   [BLOCK_SPEC.md](BLOCK_SPEC.md).
2. Add `blocks/<id>/README.md`: what it shows, which upstream API it uses, that
   API's rate limits and terms, and what each parameter means.
3. Optionally add `blocks/<id>/screenshot.png` — a crop of the block as rendered
   on a panel. The firmware repository's `tools/render_preview.cpp` produces
   these from the real drawing code.
4. Validate locally, then open a pull request:

   ```sh
   python3 tools/validate_blocks.py
   ```

   CI runs the same validator on every PR, plus `pytest`, which re-verifies
   every published `.epb` and the index against `keys/epaper-blocks.pub.pem`,
   checks each envelope carries the keyid stock firmware trusts, and checks
   `index.json` is current and inside the portal's 24 KB fetch cap:

   ```sh
   pip install cryptography pytest && pytest -q
   ```

You do not sign anything. On merge a maintainer re-signs with the registry key
and regenerates `index.json` (`./rebuild.sh`).

## Review checklist

A reviewer checks these; the validator enforces the mechanical ones and the
device enforces the rest at install time.

- `source.url` is `https://`, on a public host, with parameters only in the path
  or query string.
- **No secrets.** Params are plain strings, numbers or choices, so an API that
  needs a token cannot be used. Prefer keyless APIs, or ones taking a
  non-secret user-supplied identifier.
- The upstream API permits this use and is not rate-limited to the point where a
  handful of devices would break it. Say so in the block README.
- Descriptor ≤ 4 KB, extracted lists ≤ 6 rows, response ≤ 16 KB.
- `id` is lowercase-kebab and matches the directory.
- `minW`/`minH` are honest: the block must be legible at that size on a 16 × 12
  grid.
- The block shows *data*. It cannot take actions, and it should not try to look
  like it can.

## Reporting a problem with a block

Open an issue. If an upstream API disappears or changes shape, the block is
removed or fixed and the index republished — devices pick that up the next time
the owner opens the Blocks tab.

## Code of conduct

Be decent to each other. Harassment or personal attacks get you removed from the
project.
