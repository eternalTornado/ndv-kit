# Unity Naming Conventions

Naming rules for Unity C#, assets, Addressables, UI Toolkit, and serialized data.

> UI Toolkit (UXML/USS, element `name`, USS class, event handler):
> [naming-ui-toolkit.md](naming-ui-toolkit.md). Asset placement: [asset-structure.md](asset-structure.md).

---

## C#

| Category | Pattern | Example |
|----------|---------|---------|
| Namespace | PascalCase, dot-separated | `Game.Combat`, `Game.UI.Inventory` |
| Class | PascalCase | `PlayerController`, `UIScreenBase` |
| Interface | `I` + PascalCase | `IModule`, `IEvent` |
| Abstract base | PascalCase + `Base` suffix | `ModuleBase`, `UIScreenBase` |
| Method | PascalCase | `Initialize()`, `LoadTable<T>()` |
| Property | PascalCase | `IsInitialized`, `TableCount` |
| Private/protected field | `_camelCase` | `_isInitialized`, `_cache` |
| Public field (non-serialized data bag) | PascalCase | `Level`, `EffectType`, `Command` |
| Constant | UPPER_SNAKE_CASE | `MAX_RETRY`, `DEFAULT_TIMEOUT` |
| `static readonly` — immutable constant-like value | UPPER_SNAKE_CASE | `PAYLOAD_SERIALIZER` |
| `static readonly` — mutable runtime state (cache/collection) | `_camelCase` | `_resourceCache` |
| Enum type + values | PascalCase | `ModuleState.Running` |
| Event | PascalCase | `OnModuleInitialized` |
| Test method | `Test_<Action>_<Condition>_<Expected>` | `Test_LoadTable_InvalidPath_ThrowsException` |

> Acronym rule: C# viết acronym PascalCase một từ (`Http`, `Id`, `Api`); một acronym không
> xuất hiện hai kiểu casing trong cùng stack. Carve-out cho acronym domain-specific (giữ
> industry casing như `PvP`) là OWNER DECISION per-project, ghi trong host rules.

### Class Suffix Conventions

| Suffix | Meaning | Typical Folder | Example |
|--------|---------|----------------|---------|
| `Config` | One row in a config/data table | `Data/` | `ItemConfig`, `SkillConfig` |
| `Instance` | Runtime entity with identity, mutable | `Model/` | `ItemInstance`, `EnemyInstance` |
| `SaveData` | Serializable snapshot for persistence | `Model/` | `PlayerSaveData` |
| `Module` | Composition root / system entry | `/` (module root) | `InventoryModule` |
| `Controller` | MonoBehaviour driving a scene object or UI | `UI/` | `InventoryController` |
| `View` | Presentation class của một UI screen (MVC pair với `Controller`) | `UI/` | `InventoryView` |
| `Element` | Custom `VisualElement` (UI Toolkit) | `UI/` | `ItemCardElement` |

---

## Files

| Category | Pattern | Example |
|----------|---------|---------|
| C# source | PascalCase, one type per file | `PlayerController.cs` |
| Test file | `Test_<ClassName>.cs` | `Test_PlayerController.cs` |
| Assembly def | `<Scope>.<Feature>` | `Game.Combat.asmdef` |
| Docs (markdown) | kebab-case lowercase | `api-registry.md` |

---

## Unity Assets

| Category | Pattern | Example |
|----------|---------|---------|
| ScriptableObject asset | `SO_<Domain>_<Name>` | `SO_Item_HealthPotion.asset` |
| Prefab (generic) | `<Type>_<Name>` | `Enemy_Goblin.prefab`, `UI_Shop.prefab` |
| Prefab variant | `<Base>_<Variant>` | `Enemy_Goblin_Elite.prefab` |
| Scene | `<Stage>_<Purpose>`; canonical entry scene MAY be single-token | `Bootstrap`, `Battle_Forest` |
| Material | `Mat_<Target>_<Variant>` | `Mat_Character_Goblin` |
| Texture | `Tex_<Target>_<Channel>` | `Tex_Goblin_Albedo` |
| Animation clip | `Anim_<Target>_<Action>` | `Anim_Goblin_Attack` |
| AnimatorController | `AC_<Target>` | `AC_Goblin` |

> EXCEPTION — asset do generator/tooling sinh (vd module composition-root SO asset): giữ
> naming của generator, không ép pattern content asset. Đây là generator concern; content
> asset mới vẫn theo bảng trên.

---

## Addressables

| Category | Pattern | Example |
|----------|---------|---------|
| Group | `AG_<Feature>` | `AG_Characters`, `AG_UI` |
| Label | kebab-case lowercase | `core`, `lang-en`, `dlc-01` |
| Address | `<feature>/<name>` lowercase | `characters/goblin`, `ui/inventory` |

---

## UI Toolkit (UXML / USS)

> SoT: [naming-ui-toolkit.md](naming-ui-toolkit.md). Bảng dưới chỉ bổ sung phần bảng đó chưa cover.

| Category | Pattern | Example |
|----------|---------|---------|
| Theme USS | `Theme_<Name>.uss` | `Theme_Dark.uss` |
| USS state class | `is-<state>` / `has-<thing>` | `.is-selected`, `.has-error` |
| USS utility | `u-<util>` | `.u-hidden` |
| USS variable | `--<scope>-<name>` | `--color-primary`, `--spacing-md` |
| Custom VisualElement class | PascalCase + `Element` suffix | `ItemCardElement` |

---

## Events & Delegates

| Category | Pattern | Example |
|----------|---------|---------|
| C# event (past tense) | `On<Subject><PastVerb>` | `OnItemAdded`, `OnStateChanged` |
| Pre-event (progressive) | `<Subject><Verb>ing` | `ItemRemoving` |
| Delegate type | `<Event>Handler` | `ItemAddedHandler` |
| EventArgs class | `<Event>EventArgs` | `ItemAddedEventArgs` |
| Event bus struct (`IEvent`) | `readonly struct` + `<Subject><PastVerb>Event` | `ItemAddedEvent` |
| Event handler method | `On<Subject><PastVerb>` | `OnItemAdded(IEvent e)` |

> Event bus struct — KHÔNG exception: mọi struct implement `IEvent` PHẢI là `readonly struct`
> tên dạng `<Subject><PastVerb>Event`. Struct thiếu suffix `Event` hoặc thiếu subject là vi
> phạm — rename về contract form và update mọi subscriber trong cùng một change.
> Command/request type là input data, KHÔNG phải event notification — không implement `IEvent`,
> không đặt trong `Events/`; nếu đang kiêm hai vai thì tách: giữ request struct làm input,
> phát event `*Event` riêng.

> EXCEPTION — the `On<Subject><PastVerb>` past-tense rule targets DOMAIN state-change events.
> Two `On*` categories are exempt and keep their natural form: (1) framework lifecycle events
> fired by the engine/app loop (per-frame tick `OnUpdate`, app-shutdown `OnAppQuit`);
> (2) progressive / in-progress-state events describing an action UNDERWAY (vd `OnReconnecting`).

---

## Serialized Fields

| Category | Pattern | Example |
|----------|---------|---------|
| Inspector field | `[SerializeField] private T _name;` | `[SerializeField] private int _maxHp;` |
| Serialized auto-property | `[field: SerializeField] public T Name { get; private set; }` | `[field: SerializeField] public int MaxHp { get; private set; }` |
| Renamed field (migration) | `[FormerlySerializedAs("<old>")]` | `[FormerlySerializedAs("_hp")] private int _maxHp;` |
