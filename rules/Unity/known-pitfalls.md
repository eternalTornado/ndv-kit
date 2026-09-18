# Known Pitfalls

Common mistakes trong Unity development. Read before implementing. Project host có thể có
pitfalls file riêng với incident cụ thể — đọc cả hai.

---

## P-01: `internal` methods are not callable from test assemblies

**Symptom:** Test code gọi `internal` methods trực tiếp → compile error (`inaccessible due
to protection level`).

**Cause:** Cross-module APIs dùng `internal` visibility; test assemblies là assembly riêng,
không access được `internal` trừ khi có `[assembly: InternalsVisibleTo("...")]`.

**Rule:** Không gọi `internal` methods trong test code. Test qua public API. Behaviour không
reach được qua public API = test đang test implementation detail — hỏi Dev.

---

## P-02: Unity 6 Object.Find API changes

`FindObjectOfType` deprecated — dùng `FindFirstObjectByType` / `FindAnyObjectByType` /
`FindObjectsByType` (và tránh cả nhóm này ở runtime path — [constitution.md](constitution.md)).

---

## P-03: Service-locator lookup trước khi startup xong

`GetModule<T>()` (hoặc tương đương) chỉ hợp lệ SAU khi module startup hoàn tất; gọi trong
`Initialize` của module khác là undefined behaviour — declare dependency để orchestrator
sắp thứ tự thay vì lookup sớm ([module-constraints.md](module-constraints.md)).

---

## P-04: Module tự self-register trong Initialize

Orchestrator own việc add-entity/registration; module tự gọi trong `Initialize` chiếm quyền
đó và có thể silently treo init của module kế tiếp. Không self-register.

---

## P-05: Addressables async — never `.WaitForCompletion()` on hot-path

Sync-block trên handle Addressables ở hot path gây hitch/deadlock risk — preload async trước,
đọc cache sau ([asset-structure.md](asset-structure.md) §Loading).

---

## P-06: `[SerializeField] private` required

Public field cho Unity-serialized data phá encapsulation —
[constitution.md](constitution.md#iii-serialization-boundary).

---

## P-07: Toast/notification cho người chơi — DÙNG hệ chung, KHÔNG tự chế mới

**Symptom:** Mỗi màn tự vẽ toast/error riêng với style + timeout khác nhau → phân mảnh, dễ
nuốt lỗi (chỉ `Debug.Log*` không báo user).

**Rule:** Báo lỗi/thông báo transient cho player đi qua MỘT hệ notification/toast dùng chung
của project (event-driven, một renderer). KHÔNG tạo cơ chế toast/error-label/popup mới cho
từng màn. KHÔNG dựng `VisualElement`/`Label` bằng code lúc runtime — element mới author trong
UXML rồi `Q<>`. **Ranh giới scene:** renderer chỉ sống ở scene có nó — scene khác dispatch
event chung sẽ không ai render; dùng cơ chế cục bộ sẵn có của scene đó hoặc thêm renderer
vào scene, không tạo pattern toast thứ ba. Dialog/confirm chưa có hạ tầng chung → hỏi Dev
trước khi tự dựng.

---

## P-08: `Q<>()` lookup cho element CHƯA có trong UXML (pending re-wire) — KHÔNG phải dead code

**Symptom:** `Root.Q("someElement")` trả null vì UXML redesign tạm bỏ element; dễ nhầm là
dead code cần xóa.

**Rule:** Lookup thuộc feature đang wire (còn subscriber/caller sống ở file khác) và element
sẽ được author lại → GIỮ code. Xóa chỉ khi xác nhận KHÔNG còn subscriber/caller. Tên string
trong `Q("…")` vẫn theo element-name camelCase để khớp khi re-wire.

---

## P-09: `m_EditorClassIdentifier` stale sau namespace/class rename — text-edit về resolved value là sanctioned fix

**Symptom:** Sau rename namespace/class, field `m_EditorClassIdentifier` trong
`.asset`/`.unity`/`.prefab` giữ tên cũ. Unity 6 KHÔNG rewrite field này qua reimport/
force-reserialize — khi `m_Script` GUID resolve được, nó là sticky fallback cache.

**Rule:** Binding thật đi qua `m_Script` GUID (namespace-independent) — GUID resolve đúng
thì hoạt động bình thường; stale identifier là inert cache, KHÔNG phải functional bug. Vẫn
sửa để on-disk trung thực: cách DUY NHẤT là targeted text-edit đúng dòng
`m_EditorClassIdentifier` về resolved value (`<Assembly>::<namespace>.<class>` hiện tại).
CARVE-OUT hẹp: text-edit riêng dòng này được phép — KHÔNG đụng `m_Script` GUID, KHÔNG đụng
`.meta`, KHÔNG hand-author asset khác.

---

## P-10: Server-provisioned config wire-casing — verify bằng endpoint DEPLOYED, KHÔNG đọc BE local source

**Symptom:** Row-mapper đọc JSON key **case-sensitive**; casing lệch với wire thật → row
drop **im lặng** (counter "applied" vẫn đếm, table rỗng, UI bind null).

**Rule:** Wire casing là ground truth của **ENDPOINT DEPLOYED** mà client thực gọi, KHÔNG
phải BE local source checkout (deployed có thể mới/cũ hơn source — đọc source dẫn tới "fix"
sai). Verify BẮT BUỘC bằng `curl "<baseUrl>/<config endpoint>"` per-table. Config table
API-sourced → casing runtime lấy theo WIRE deployed, không suy từ convention; nếu một table
serve casing khác, client đọc nguyên wire, KHÔNG "sửa cho khớp convention". Sub-object có
thể mang casing riêng độc lập top-level — mapper iterate `prop.Name`, không hardcode.

---

## P-11: Case-only file rename phá MonoScript mapping per-machine

**Symptom:** Rename chỉ đổi casing (`Foo` → `FoO`) để lại `GetClass()==null` / Missing
Script không error trên máy khác.

**Rule:** Sau case-only rename: touch file + force sync reimport; nhớ `Library/` là
per-machine — teammate cũng phải reimport.

---

## P-12: Edit-mode probe cleanup — dùng `DestroyImmediate`

`Object.Destroy` bị queue và silently no-op trong edit mode; GameObject vứt tạm từ
probe/tool leak vào scene. Edit-mode cleanup dùng `DestroyImmediate`.
