# Keys

`epaper-blocks.pub.pem` is the public half of the key this registry is signed
with (keyid `epaper-blocks-2026`). The private half is held offline by the
maintainer and is not in any repository.

Verify anything published here without a device:

```sh
python3 tools/block_sign.py verify keys/epaper-blocks.pub.pem index.json
python3 tools/block_sign.py verify keys/epaper-blocks.pub.pem blocks/uv-index/uv-index.epb
```

The same PEM is compiled into the firmware as a trust anchor
(`firmware/epaper_dashboard/trusted_keys.h`). To run your own registry, mint
your own key with `tools/block_sign.py keygen`, keep the private half offline,
and put your public half there instead — see [../SECURITY.md](../SECURITY.md).
