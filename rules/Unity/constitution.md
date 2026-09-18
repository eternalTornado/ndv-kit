# Unity Project Constitution

Core engineering principles for Unity projects. Non-negotiable rules that supersede informal
agreements documented in comments, READMEs, or verbal discussions.

---

## Core Principles

### I. Logging & Observability

All log messages MUST use prefix format: `[ClassName] event-name: detail`.

| Situation | Method |
|---|---|
| Expected lifecycle events (save completed, module init, scene loaded) | `Debug.Log` |
| Recoverable issues (missing optional dependency, fallback activated) | `Debug.LogWarning` |
| Unrecoverable errors (system failure, corrupt save data) | `Debug.LogError` |

`Debug.Log*` calls are stripped from IL2CPP release builds via scripting define. Do not rely
on logs for runtime correctness.

### II. External Integrations

Third-party SDKs (analytics, ads, push, networking, audio middleware, crash reporting) MUST
be wrapped in adapter modules. Core code MUST NOT reference SDK types directly — this allows
swapping, mocking, or stubbing SDKs without touching business logic.

### III. Serialization Boundary

- Inspector-exposed fields MUST use `[SerializeField] private` — never `public` fields for
  Unity-serialized data.
- Use `[field: SerializeField]` for serialized auto-properties rather than public backing fields.
- Use `[FormerlySerializedAs("oldName")]` when renaming any serialized field — removing the
  attribute later loses editor-authored data.
- EXCEPTION: Timeline `PlayableBehaviour` template fields MAY be `public` — the Unity Timeline
  clip-template + mixer pattern reads/copies them by field, and forcing `[SerializeField]
  private` breaks clip binding. This mirrors the `[UxmlElement]` `partial` exception.

### IV. Testing

Test policy per [../Shared/constitution.md](../Shared/constitution.md#testing-policy) —
host rules define; kit default là không generate test code trừ khi user yêu cầu.

---

## Unity Constraints (Unity 6 API Compliance)

| Rule | Rationale |
|---|---|
| `DontDestroyOnLoad` only on a single global root GameObject | Centralizes global singleton pattern; per-scene objects stay in their scene |
| Never create `.meta` files manually | Unity auto-generates correct GUIDs on import; manual creation produces mismatches |
| No `#region` | Hides code structure; `#region` collapses are a symptom of classes that are too large |
| No `partial class` — EXCEPT `[UxmlElement]` custom `VisualElement` | Splits class contract across files; creates implicit coupling. Exception: Unity 6 UI Toolkit's `[UxmlElement]` source generator REQUIRES `partial` on the element class |
| `internal` visibility for cross-class-within-module APIs | Prevents accidental use outside the module boundary |
| Do not create `.asmdef` files automatically | Assembly definitions must be created manually by developers, not by AI or automated tools |
| Avoid `FindObjectOfType` / `GameObject.Find` at runtime — EXCEPT play-mode dev/test tools under a `Test/` folder | Slow O(n) scene walk; indicates missing dependency wiring. Exception: a play-mode dev/test harness may one-shot auto-discover objects in an arbitrary showcase scene — it never ships in a gameplay path |
| Do not reference scene objects from `ScriptableObject` assets | SO assets outlive scenes; produces dangling references |

---

## Governance

This constitution supersedes all other conventions documented in comments, READMEs, or
informal agreements within the Unity stack rules. **Amendments** require a written rationale
and a migration note.
