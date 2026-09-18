---
paths:
  - "**/*.cs"
  - "**/*.csx"
---

# Unity Patterns — world / module / hot-path contracts

> Cross-cutting principles (logging format, SDK adapter, Unity constraints table):
> [constitution.md](constitution.md). Naming: [conventions.md](conventions.md).
> File này chỉ giữ world / module / hot-path contracts. Áp dụng khi project dùng kiến trúc
> module-system (composition root + event bus); project không dùng → host rules thay thế.

## Event Bus & World Isolation

Each world/event-bus instance is an isolated event bus + entity registry.
Events MUST NOT leak across world boundaries.

- The registry's add-entity API is the sole place that binds `entity.World`.
  Game code MUST NOT assign the world reference directly.
- Identity sources are fixed by entity category:
  - ScriptableObject / MonoBehaviour entities → `GetInstanceID()`
  - Server-assigned game entities → server-provided integer set before registration
  - Ephemeral runtime objects → private counter owned by the creating system
- Multiple worlds MAY coexist (vd global app world + per-battle world).
  A bridge module MUST be used when events must cross worlds.
- IDs are unique within one world instance, not globally.

## Module Shape (folder + composition-root placement)

- One module = ONE composition-root class (marked by the framework's module attribute),
  đặt tại module ROOT folder. Composition-root đặt trong subfolder — kể cả `Adapter/` —
  bị CẤM: module khi đó có hai module-root. Adapter wrap SDK/HTTP là plain class do root
  module own/register (hoặc tách thành module riêng có root đúng chuẩn), không phải
  composition-root thứ hai.
- Layer folder per module là CLOSED list: `Data/ Model/ Logic/ Events/ Adapter/ Interfaces/`
  (+ `<Name>Module.cs` ở root). UI screen KHÔNG nằm trong module — tập trung ở UI feature
  home của project. Folder đặc thù ngoài list chỉ hợp lệ khi được declare trong module
  register của project; folder undeclared là vi phạm — hoặc fold vào closed layers, hoặc
  declare vào register.
- `Logic/` và `Model/` KHÔNG import `UnityEngine` và KHÔNG làm IO — phải 100% unit-testable,
  compile được khi remove Unity. Logging trong `Logic/` đi qua abstraction thuần C# (inject
  qua `Interfaces/`), không `UnityEngine.Debug`.

## Hardcoded Content (environment / balance / routes)

- Route/endpoint string sống ở MỘT endpoint registry duy nhất; mọi call site reference
  registry đó. Route literal rải rác per-adapter, hoặc registry tồn tại nhưng không call
  site nào import (hai SoT lệch nhau), đều là vi phạm.
- Backend host/base-URL là environment concern: load từ build/environment config, fail fast
  khi unset ở non-editor build. Localhost chỉ được phép làm editor-only dev default —
  không bake host vào code constant hay prefab default rồi ship.
- Balance/tuning data từ GDD (scoring weights, damage constants, rate) KHÔNG bake vào C# —
  sống ở data-table config để rebalance là một data edit, không phải client recompile.
  Constant thuộc parity surface client↔server (replay determinism): extract vào config cả
  hai tier cùng consume; giữ dạng parity-locked code constant CHỈ khi có owner decision
  ghi lại.
- Operational knob (cache TTL, retry count, threshold) config-driven — không `const`
  literal compile cứng.

## Module System Contract

Áp dụng khi framework module-system của project có lifecycle init:

- `Initialize(onComplete, onFailed)` MUST call exactly one callback, exactly once. Calling
  both, or calling either more than once, is a bug.
- Required modules are fatal: startup halts on `Initialize` failure. Optional modules:
  `LogWarning` + skip.
- Service-locator lookup (`GetModule<T>()`) is valid ONLY after startup completes. Calling
  it during startup is undefined behaviour.
- Module registration assets do tooling/generator của framework sinh — MUST NOT be created
  by hand.
- Module KHÔNG tự self-register vào registry trong `Initialize` — orchestrator own việc
  registration; module self-register chiếm quyền orchestrator và có thể treo init của
  module kế tiếp ([known-pitfalls.md](known-pitfalls.md)).

## Hot-Path Allocation Budget

Hot paths include: `Update`, the dispatch loop body, gameplay pipeline execution,
simulation tick.

- LINQ MUST NOT be used on hot paths (allocates enumerators and closures).
- String concatenation MUST NOT be used on hot paths (allocates).
- Per-entity allocations inside dispatch loop body are FORBIDDEN.
  One snapshot allocation per dispatch call is the accepted maximum.
