# PostgreSQL schema standard

This standard governs naming, keys, data types, and integrity for the game server database
(PostgreSQL). Estate divergence is an audit finding.

## Scope

Covers: topology, table/column naming, PK/FK, data types, JSONB, timestamps, integrity,
indexes, soft-delete, the stackable-vs-instanced item model, and economy operations. Does
NOT cover: migration file layout, client-side persistence, concrete id values
([../Shared/id-plan.md](../Shared/id-plan.md) + host id table).

## Rules

### Topology

- Project multi-zone: schema two-tier — per-zone CLUSTER (gameplay `config_*`, `player_*`,
  `*_log`) và cross-zone GLOBAL (identity, fleet, ops, `gm_*`, redeem). Identity
  (account/session) MUST live only in GLOBAL, never duplicated per zone. Project single-zone:
  một tier, các rule còn lại vẫn áp.

### Naming

- Read-only config tables MUST be prefixed `config_`.
- Player-owned entity/instance tables MUST be prefixed `player_`. Exceptions:
  domain-operational state tables keyed with `player_id` and append-only tables, named by
  domain — legal.
- Append-only tables MUST end in `_log`/`_ledger`; live-ops tables MUST be prefixed `gm_`.
- Table and column names MUST be snake_case.
- Table names MUST use the canonical glossary term của project — banned stems (legacy
  synonyms) map về canonical trong glossary.
- Column names MUST NOT be abbreviated and MUST avoid SQL reserved words (`currency_amt` →
  `currency_amount`; `group` → `set_group`).
- An entity-catalog config table (one with a displayed identity) MUST carry a `code` column
  (the design code_id, UNIQUE, for GDD traceability only — never on the wire) và một display
  name column theo locale chính của project. A lookup/curve/rule config table (keyed by
  level/rarity/tier) does NOT require these two columns.

### Keys

- An entity table's PK MUST NEVER be VARCHAR — a string business key becomes an INT id PK +
  a VARCHAR UNIQUE `code` column. Exception: KV/flag tables with NO inbound FK whose lookup
  is inherently by string — a natural/composite string key is legal because no join gets
  slower.
- A player-state composite PK MUST encode exactly the business rule that constrains it
  (vd PK (`player_id`, `config_id`) = one copy per player).
- An instanced item table MUST use a surrogate UUIDv7 with a PK prefix (`player_id`, `id`)
  for a range-scan of the whole bag; an append-only high-write table MUST use a UUIDv7 with
  time-in-PK (`id`, `created_at`) ready for partitioning.
- FK columns MUST be named `<entity>_id`; a hard FK is preferred where enforcement improves
  safety.
- The player identifier MUST be `player_id` UUID, and every player-owned table MUST FK to
  it; the column name MUST be uniformly `player_id` — never `user_id`.
- FKs MUST NOT use `ON DELETE CASCADE` / `SET NULL` — the default MUST be RESTRICT; deleting
  a root (player/account) goes through soft-delete (see below).

### Types

- A config value MUST be a self-describing flat column, not an index-encoded array
  (`base_stats[13]` → `base_hp`/`base_atk`/…).
- Rolled stats with a fixed slot count that need ORDER BY/filter MUST be flat columns, not
  JSONB.
- A hot-path currency balance MUST be a denormalized wallet column (BIGINT ≥ 0 per
  currency), not a JSONB blob.
- JSONB MUST be used only for a genuinely sparse/variable map.
- Boolean columns MUST be prefixed `is_`.
- A derived value (current rarity, level_cap, precomputed stat) MUST NOT be stored — it is
  recomputed from config at load time.
- Timestamps MUST be `created_at` / `updated_at` / `deleted_at`, set server-side via `now()`.
- Gameplay/balance/state values MUST be INTEGER — currency is BIGINT; a rate/percent is
  permille INT/SMALLINT (comment `-- permille`); `FLOAT`/`REAL`/`DOUBLE PRECISION`/`NUMERIC`
  are BANNED in `config_*`/`player_*`/log tables (integer-only to preserve client↔server
  replay parity).
- NOT NULL MUST be the default — a column is nullable only when NULL carries business
  meaning; counters/flags MUST declare a DEFAULT right in the DDL.
- Enum values MUST be stored as SMALLINT + a mapping comment in the DDL — no PG native ENUM.

### Index

- Indexes MUST be named by kind: `idx_<table>_<cols>` (btree), `uq_<table>_<cols>` (unique),
  `brin_<table>_time` (BRIN on `created_at` for append-only tables); a partial index when
  the predicate is clear. A new index MUST be added only with query evidence — no
  speculative indexing.

### Integrity

- Item taxonomy MUST be enforced by a CHECK guard against the id-plan ranges, not by
  trusting the caller.
- An append-only ledger MUST REVOKE UPDATE/DELETE at the database layer, not just by
  convention.
- Per-player keyed state MUST upsert ON CONFLICT by the natural key; hot-path state (wallet)
  MUST carry a `version` column for optimistic locking.
- A quantity/balance column MUST have a CHECK (>= 0); a ledger delta column MUST have a
  CHECK (<> 0).
- A root identity (account, player) MUST be deleted by soft-delete `deleted_at` — the row is
  kept for ledger integrity; queries MUST filter `deleted_at IS NULL` by default;
  hard-delete/erasure goes only through a controlled ops procedure, never through the
  gameplay API.

### Item model — stackable vs instanced

- Items with the same config and no per-instance state MUST collapse into a quantity:
  currency (a `player_wallet` column), material/shard (`player_item`, PK (`player_id`,
  `config_id`)).
- Items where each copy carries its own rolled stats MUST keep separate instances
  (equipment/artifact tables). Id ranges per host id table.

### Economy & operations

- Every currency mutation MUST be server-authoritative and MUST write `wallet_ledger` with a
  `reason` + `idempotency_key` + `correlation_id`; a replay with the same idempotency_key
  MUST create no new ledger entry.
- Stamina/energy MUST be treated as a resource (not a currency), co-located in
  `player_wallet`: store `stored` + `regen_anchor_at`; the current value is computed at read
  time `min(cap, stored + ⌊elapsed/interval⌋)`; `cap`/`interval` derive from config — not
  stored per-row, no tick job; written only on spend/refill.
- GM/live-ops tables MUST live in GLOBAL with a `scope` column — the cluster MUST NOT
  duplicate GM tables.
- A table with no spec MUST NOT enter the schema — it lives in the schema file's DEFERRED
  section; adding it later is a NEW table, zero migration risk.
