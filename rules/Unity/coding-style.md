---
paths:
  - "**/*.cs"
  - "**/*.csx"
---

# C# Coding Style

> Extends [../Shared/coding-style.md](../Shared/coding-style.md) with C#-specific content.

## Standards

- Follow current .NET conventions and enable nullable reference types
- Prefer explicit access modifiers on public and internal APIs
- Keep files aligned with the primary type they define

## Naming

Naming (C# identifiers, files, assets, UXML/USS, events, serialized fields) — SoT ở nơi khác,
không lặp bảng tại đây:

- [conventions.md](conventions.md) — bảng naming cụ thể cho Unity client.
- [naming-ui-toolkit.md](naming-ui-toolkit.md) — UI Toolkit: UXML/USS file, element `name`,
  USS class, event handler.

## Formatting

- Use `dotnet format` for formatting and analyzer fixes
- Keep `using` directives organized and remove unused imports
- Prefer expression-bodied members only when they stay readable

## Warnings — fix at root cause

- Compiler/analyzer warnings MUST be fixed at the ROOT CAUSE, not suppressed. Removing the
  symptom without removing the cause is not a fix.
- `#pragma warning disable`, `[SuppressMessage]`, `[Obsolete]`-silencing, and analyzer
  opt-outs are BANNED as a warning fix. Typical root-cause fixes: CS0067 (event never used)
  → raise it or delete the dead event + its subscribers; CS0414/CS0169/CS0649 (unused field)
  → delete it; CS1998 (async without await) → make the member non-async / `abstract` /
  return a completed awaitable; CS0114 (hides inherited) → `override` + `base` call or drop
  the shadow.
- Suppression is NOT allowed
