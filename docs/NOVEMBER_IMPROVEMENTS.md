# Offline URL parsing

The URL normalizer handles malformed authorities without crashing, rejects credential-bearing and nonstandard-port URLs, and canonicalizes accepted public-route URLs without query/fragment data. Tests use synthetic local inputs only; no extraction or content download is performed.
