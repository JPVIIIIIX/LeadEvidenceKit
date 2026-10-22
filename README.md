# LeadEvidenceKit

**Evidence-aware customer research reports for sales teams.**

LeadEvidenceKit checks the structure and evidence links in a customer research
packet, then renders a Markdown report separating attributed findings, candidate
references, unknowns, and source coverage. It works offline with no runtime
dependencies on Python 3.11+.

**It checks consistency, not truth.** Identity confirmation, source attribution,
excerpts, and claim labels are supplied by the caller. The kit does not establish
that a source is authentic or that an excerpt supports a claim.

## Quick start

From a repository checkout:

```sh
python3 -m pip install .
leadevidencekit examples/synthetic.json --check
leadevidencekit examples/synthetic.json > report.md
```

Or run directly without installation:

```sh
PYTHONPATH=src python3 -m leadevidencekit examples/synthetic.json
```

The bundled example uses fictional organizations and reserved `.example` domains.
It is not a customer record or a measured research result. No PyPI publication is
claimed; install from this checkout.

## Python API

```python
import json
from leadevidencekit import render_markdown, validate_report

with open("examples/synthetic.json", encoding="utf-8") as source:
    packet = json.load(source)

errors = validate_report(packet)
if errors:
    raise ValueError(errors)
print(render_markdown(packet))
```

## Input contract

| Field | Meaning |
| --- | --- |
| `subject` | Nonempty customer or research-subject label |
| `identity` | Caller-assessed `confirmed` or `unconfirmed` |
| `sources` | Array of source objects described below |
| `claims` | Array of statements with explicit evidence roles |

Each source has a unique `id` (letters, digits, underscores, hyphens), an HTTP(S)
`url`, a `status`, and an explicit boolean `attributed`. A `read` source also
requires a nonempty `quote`. Other statuses are `candidate`, `blocked`,
`not_found`, and `not_run`; none is treated as a successfully read source.

Each claim has nonempty `text`, a `kind` (`fact`, `candidate`, or `unknown`),
and optional `source_ids`. Every referenced ID must exist. A `fact` requires a
confirmed subject and at least one source; every cited source must be `read` and
explicitly attributed. This is a conservative structural rule, not automated
identity resolution or semantic verification. Candidate claims and unknowns do
not upgrade identity or imply purchasing authority.

An empty sources/claims array is permitted: the output states that nothing was
recorded. Unknown fields are ignored and are not rendered. There are no default
industry scores, star ratings, CRM field names, or hidden company policies.

## Scope and boundaries

- Reads a local JSON file and prints a report or validation errors.
- Makes no network requests and does not execute report content.
- Does not search websites, collect customer data, log into services, call models,
  write CRM records, send messages, or manage user permissions.
- Escapes Markdown/HTML in supplied prose and rejects credential-bearing,
  non-HTTP(S), or unsafe link syntax. URLs are not fetched; this is not an SSRF
  defense for applications that later choose to fetch them.
- Does not redact personal data. Review your input and generated reports before
  sharing them. CLI errors are local diagnostics, not an audit trail.

For sales delivery, use this library behind an application that supplies its own
authentication, customer access control, storage, source acquisition, and review
process. No deployed sales service or production acceptance is implied.

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Tests cover evidence-state boundaries, malformed input, dangerous link/prose
handling, and the CLI. They use synthetic data and do not access external services.
CI runs the suite on Python 3.11 through 3.14. Local verification details are in
the GitHub release/task report; a configured CI workflow alone is not a passing run.

## Contributing

Small, tested fixes and synthetic reproductions are welcome. Do not submit
customer records, real contact details, tokens, cookies, private URLs, or internal
configuration. Keep source-status and evidence-role distinctions explicit.

## Origin and license

This standalone implementation was informed by evidence-handling patterns from a
private customer research workflow. It shares no runtime dependency or Git history
with that system and does not ship its CRM connectors, company policies, customer
fixtures, or account sessions. It is an early 0.1.0 library, not the full private
research product. Released under the MIT license; see [LICENSE](LICENSE).
