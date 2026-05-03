# ASINT

This repository contains the analysis scripts and data accompanying the ASINT
paper, together with the full ASINT source code.

## Source code (pre-release)

The ASINT source code under [source_code/](source_code/) is currently a
**pre-release** snapshot. Running the full pipeline end-to-end is non-trivial:

- It requires **two crawling machines** and **one GPU machine with at least 4×
  A100s**.
- Cross-machine file transfers (raw HTML, NER outputs, LLM classification
  artifacts) are handled by scripts, but the actual deployment still has to be
  adapted to the operator's machine configuration (paths, credentials, GPU
  topology, network reachability between the crawl and GPU hosts, etc.).
- A traditional Docker image is not a viable shortcut here either, because the
  pipeline relies on heavy compute resources (multi-GPU inference, large NER
  and LLM models) that don't fit a single self-contained container.

After the review period, we will release a complete **one-click solution**
that orchestrates the full pipeline across machines, and we are happy to
provide setup support in the meantime.

## Org-Family snapshots

Monthly snapshots of the ASINT AS-to-organization clustering, one folder per
month. Each folder contains a single file:

```
<YYYY-MM>/saint.org_families.json
```

### File format

A JSON array of **alias-group** records. Each record has:

| Field           | Type      | Description                                                                                                                              |
| --------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `alias_id`      | int       | Alias-group identifier. One alias group ≈ one operating entity.                                                                          |
| `org_family_id` | int       | Org-family identifier. Multiple alias groups sharing the same `org_family_id` are linked by parent/child ownership and form one family.  |
| `asn_entries`   | list[obj] | ASNs belonging to this alias group, each with `asn`, `as_name`, `org_name`, `rir`.                                                       |
| `parent`        | list[int] | `alias_id`s of parent alias groups (ownership / acquirer side).                                                                          |
| `children`      | list[int] | `alias_id`s of child alias groups (subsidiary side).                                                                                     |
| `_id`           | obj       | Internal record id; can be ignored.                                                                                                      |

Example record:

```json
{
  "alias_id": 4622,
  "org_family_id": 759,
  "asn_entries": [
    {"asn": 151205, "as_name": "HSBC-INM-AS-AP", "org_name": "hsbc", "rir": "apnic"}
  ],
  "parent": [],
  "children": [4609]
}
```

### Two granularities

- **Alias group** (`alias_id`): tightest grouping — ASNs that belong to the
  same operating entity.
- **Org family** (`org_family_id`): broadest grouping — alias groups merged
  via parent/child links (e.g. a holding company and its subsidiaries).
