# Offline URL parsing

The URL normalizer handles malformed authorities without crashing, rejects credential-bearing and nonstandard-port URLs, and canonicalizes accepted public-route URLs without query/fragment data. Tests use synthetic local inputs only; no extraction or content download is performed.

Offline parser CI now runs synthetic tests on every push/PR. The optional local recovery-archive assertions remain intact and are explicitly skipped when that non-distributed input is absent; no historical records or answers are manufactured.

`python validate_jsonl.py path/to/questions.jsonl` performs a read-only, offline structural preflight with JSON diagnostics and a failing exit status for malformed records, duplicate IDs and out-of-range/duplicate answer indexes. Missing answers remain missing. This is not content approval, answer verification or an authoritative inventory reconciliation.
