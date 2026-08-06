<!-- Adding or changing a block? Keep the checklist. Anything else, delete it. -->

## What this block shows



## Upstream API

- Endpoint:
- Requires a key: no <!-- blocks cannot hold secrets; "yes" means it can't be accepted -->
- Rate limits / terms:

## Checklist

- [ ] `blocks/<id>/block.json` exists and `id` equals the directory name
- [ ] `blocks/<id>/README.md` explains the block, the API, and every parameter
- [ ] `python3 tools/validate_blocks.py` passes locally
- [ ] `source.url` is `https://` on a public host, no secrets in params
- [ ] `minW`/`minH` are the sizes at which it is actually legible
- [ ] Screenshot added (optional, but it shows up in the store)

I have **not** signed anything — a maintainer re-signs and republishes the index
on merge.
