# PC Basketball 2024 — data digest

Short notes for a data scientist. Variable details live in each workbook’s **`codebook`** sheet.

**Study / methods draft:** [Google Doc](https://docs.google.com/document/d/1d0SUs7lyrAU2AqFaAXRNIpx6RZ_MyiT2Nk4RSL6nAbI/edit?usp=sharing)

## Task (game)

Non-immersive VR basketball serious game. In each bout the player takes repeated shots under timed conditions; court position and game speed vary. Aim: hit the basket. Sample: **n = 50** (25 cerebral palsy / 25 age–sex-matched controls), up to **10 protocol days**.

## Files & grain

| File | Sheet | Grain | Size (this release) |
|------|--------|--------|---------------------|
| `users.xlsx` | `users` | 1 row = participant | 50 × 515 |
| `matches.xlsx` | `matches` | 1 row = match/bout | 790 × 57 |
| `balls.xlsx` | `balls` | 1 row = shot attempt | 11 703 × 11 |

Every file also has a `codebook` sheet (`variable_name`, `variable_label`, `description`, `data_type`, `unit`, `value_labels`).

## Logic / joins

```
users.id_user  ←──  matches.id_user
matches.id_match  ←──  balls.id_match   (full extract)
```

- **Attempt models** use shot-level `is_hit` (+ position, timing, etc.).
- **Match descriptives** use aggregates (`hit_rate`, `n_shots`, timing summaries).
- **This `balls.xlsx` is a narrow slice** (no `id_match`). To link shots → matches → users, restore `id_match` from the full balls table.

## Key codes (quick)

| Variable | Where | Codes |
|----------|--------|--------|
| `group` | users | `cp` / `control` (strings) |
| `group` | matches | `0` = CP, `1` = control |
| `block` | matches | `1` = days 1–2; `2` = 3–5; `3` = 6–10 |
| `speed` | matches | ordinal 1–4 (game setting) |
| `current_position` | balls | `1` left, `2` centre, `3` right |
| `is_hit` | balls | `0` miss, `1` hit |
| `is_same_position` | balls | `1` same as previous shot, `0` changed |
| `gmfcs` / `macs` | users | levels I–V; CP only |

## Derived facts worth knowing

- Match `hit_rate ≈ round(n_hits / n_shots, 2)`.
- Many `matches.*time_between*` / `m1_*` / `m2_*` fields are **pre-aggregated** from shot-level `time_between`, often stratified by hit/miss, same/change position, or match half (`half`).
- Shot `time_between` = ball-hold / prep time; `time_remaining` = seconds left in the bout.
- Protocol mentions ~60 s bouts; recorded `total_time` is often **45** s in this extract.
