# Go server structure

This standard governs how the game server source (Go) is laid out — packages, layers,
wiring, errors, transactions, logging. It is a criteria source that new code and spec/TDD
generation comply with; estate divergence is an audit finding.

## Scope

Covers: package layout, the api-module pattern, dependency boundaries, error/tx/logging
conventions, shared constants, migrations. Does NOT cover: identifiers cụ thể, DB
([db.md](db.md)), client. API contract format (OpenAPI/proto) is per-project — settled when
the project mints its api standard.

## Rules

### Naming

- Package name MUST be lowercase, one word, no underscore; import path
  `<project-module-path>/internal/<package>`.
- Identifiers MUST be MixedCaps: exported `PascalCase`, unexported `camelCase`, no underscore
  — constants included (`maxRetry`, `DefaultTimeout`; never `MAX_RETRY`).
- Acronyms keep Go casing (`ID`, `HTTP`, `URL`) and MUST be spelled one way across the
  stack; a datum crossing tiers keeps its stem and changes casing only
  ([../Shared/coding-style.md](../Shared/coding-style.md)).
- File names MUST be `snake_case.go`; tests `<file>_test.go`; persistence adapter
  `<store>_repo.go` (see §Layer & dependency).
- Business error sentinels `Err<Reason>` per §Error, transaction, logging.

### Package & wiring

- One server module MUST be one package `server/<package>/`. A NEW package MUST take the
  project glossary domain name; a legacy package keeps its native name + an alias in the
  module register. Carve-out: a large domain MAY be decomposed into a multi-level subpackage
  tree — still ONE domain module, its components declared in the register.
- A package that exposes HTTP MUST have an `api/` subpackage with at minimum `module.go` +
  `handler.go` + `dto.go`.
- `api/module.go` MUST be where wiring happens (repo, service, handler) and MUST expose a
  single route-registration entry point; every module MUST be constructed + registered at
  the composition root (`bootstrap/app.go` hoặc tương đương) — no self-registration.
- HTTP request/response types MUST live only in `api/dto.go`; the transport shape MUST NOT
  leak into the domain package.
- A large package MUST split into component subpackages, imported as
  `<project-module-path>/internal/<package>/<component>`.

### Layer & dependency

- A domain file (entity + game rules) MUST have zero external deps — no framework/driver
  import; a service MUST depend only on the repository interface, never on an
  implementation; the persistence adapter MUST be `<store>_repo.go` placed at the root of
  the package (or subpackage) that OWNS that table — swapping persistence MUST NOT touch
  the service.
- One use case MUST be one public verb+noun method on the service (`LevelUpHero`,
  `PurchaseItem`) — never several use cases merged into one method.
- Shared constants (currency ids, id-range bounds) MUST be defined in ONE place — the
  package that owns that domain; other packages import, never redeclare. Range values per
  [../Shared/id-plan.md](../Shared/id-plan.md) + host id table.
- `shared/` MUST be cross-cutting and depend on no module; `pkg/` MUST be generic with zero
  domain knowledge; the entry point `cmd/<bin>/main.go` MUST only bootstrap + wire.

### Error, transaction, logging

- A business error MUST be a sentinel `Err<Reason>` (`errors.New`) declared in the owning
  package's domain file, its message prefixed by package; callers MUST compare with
  `errors.Is`, the handler maps a sentinel → HTTP status — NEVER string-matching the error
  message.
- The transaction boundary MUST be at the service: one use case = one transaction the
  service opens/closes; the repo MUST NOT open its own tx. Cross-system flow (saga vs long
  tx) is per-project decision, not decided in this standard.
- Logging MUST go through `log/slog` (stdlib) — no `fmt.Print*`/`log.Print*` in module code;
  `context.Context` MUST be the first parameter of every service/repo method and MUST be
  propagated down to the query/HTTP call.

### Repo-root artifact

- Migrations `db/migrations/NNN_<slug>.up/.down.sql` MUST be APPEND-ONLY — old files MUST
  NOT be edited.
