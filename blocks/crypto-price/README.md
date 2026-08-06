# Crypto price

Spot price in USD for Bitcoin, Ethereum, Dogecoin or Monero from
CoinGecko's keyless public endpoint, rounded to whole dollars.

CoinGecko rate-limits anonymous callers fairly aggressively; at the
dashboard's minimum 3-minute refresh you may still see an occasional
`HTTP 429`, which shows as a fetch error and clears on the next cycle.
If you want the 24-hour change as well, use the `crypto-24h` block
instead. Suggested size: 5x3.
