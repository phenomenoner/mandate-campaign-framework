# tools

Thin kernel-facing CLIs:
- `validate-mandate.py` — validate kernel v0.1 mandate fields
- `init-campaign.py` — create campaign directory + canonical mandate/state/initial receipt
- `advance-campaign.py` — run one bounded dispatcher step against a file-backed campaign
- `inspect-campaign.py` — inspect state + receipts in human-readable or JSON form

Shared helper:
- `_runtime_lib.py`

Runtime dependency:
- `PyYAML` (`yaml.safe_load`) is required for mandate/defaults parsing.

Design rule:
- keep these CLIs thin and kernel-facing.
- do not hide adapter domain logic here.
- keep phase transition semantics explicit (forward/retry/back/fail) in dispatcher validation, not implicit worker behavior.

Runtime tests:
- `../tests/test_runtime_schema_fixtures.py`
- `../tests/test_phase_transition_semantics.py`
