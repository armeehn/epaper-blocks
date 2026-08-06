# Stock price

Last traded price plus previous close for any Yahoo Finance symbol.
Index symbols work: `^GSPC` (S&P 500), `^IXIC` (Nasdaq), `^DJI` (Dow).

Caveat: this is Yahoo's unofficial chart endpoint. It is widely used by
hobby projects and needs no key, but Yahoo can rate-limit or change it at
any time; expect an occasional `HTTP 429` under heavy use. Suggested
size: 5x3, or 5x4 to see the previous-close line.
