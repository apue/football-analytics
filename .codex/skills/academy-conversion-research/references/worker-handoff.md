# Worker handoff

Return one JSON object or an equivalent concise message with:

```json
{
  "run_id": "...",
  "shard_id": "...",
  "status": "complete|blocked|needs_review",
  "manifest_path": "...",
  "output_paths": ["..."],
  "item_counts": {
    "assigned": 0,
    "complete": 0,
    "failed": 0,
    "quarantined": 0
  },
  "validation_path": "...",
  "exceptions": [
    {"item_id": "...", "reason": "...", "evidence_path": "..."}
  ],
  "checks_run": ["..."],
  "checks_not_run": ["..."]
}
```

Do not paste raw pages or secrets into the handoff. Do not summarize a failed
item as absent data. Do not claim the full run is complete; only the supervisor
can merge and validate all shards.
