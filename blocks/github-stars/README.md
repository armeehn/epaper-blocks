# GitHub stars

Star count and open-issue count for any public repository, via the
unauthenticated GitHub REST API. Set `repo` to an `owner/name` string.

Unauthenticated requests are limited to 60 per hour **per public IP**,
which is comfortable at the dashboard's refresh rates but is shared with
anything else on your network calling the same API. Private repositories
are not reachable — the API needs a token, and blocks intentionally cannot
carry secrets. Suggested size: 5x3.
