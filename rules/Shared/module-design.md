# Module design — MD rules

Luật thiết kế ranh giới module, cross-stack. `module-architect` áp khi viết blueprint (§Mode
blueprint), reviewer cố refute theo từng rule (§Mode blueprint-review). Thuật ngữ `band`, `Layer k`,
`buildMode`, `role` định nghĩa duy nhất ở `/ndv-blueprint` SKILL §Thuật ngữ; schema blueprint ở
agent `module-architect` §Artifact blueprint.json.

Cột **Check**: `S!` = `ndv_blueprint.py --check` blocking · `S?` = script warning, triage ở gate ·
`R` = reviewer defect · `G` = decision cho user. Ngưỡng số có ghi "(kit)" không có nguồn ngoài —
chỉ được là warning hoặc review signal, không bao giờ blocking.

## A. Ranh giới

| ID | Rule | Check | Nguồn |
|---|---|---|---|
| MD-01 | Mỗi module giấu MỘT quyết định thiết kế có khả năng đổi (secret). `value` nêu secret + change driver, cite bằng chứng biến động trong GDD (open decision, gap, proposal, tunable range, nội dung LiveOps). Hai module cùng secret → gộp. Secret chỉ là diễn đạt lại tên module → chưa có secret. | R | Parnas 1972 "On the Criteria…"; Löwy, *Righting Software* ch.2 |
| MD-02 | Không cắt module theo bước của loop. Thứ tự loop sống ở band loop và tối đa một module điều phối. | R | Parnas 1972 (flowchart decomposition) |
| MD-03 | GDD có bảng system / architecture → mỗi row seed một module. Mỗi split / merge so với bảng là decision `boundary` nêu MD id fail. Không cap số module. | R, G | BMAD architect "ratify"; đo trên mutant ở research kit |
| MD-04 | Coverage: mọi mechanic, system, state của GDD map vào `sources` của ≥1 module, hoặc `outOfScope` kèm lý do. Không coi section vắng là requirement vắng. | S? (`unread-file`, `uncovered-file` — mức file), R | Gotel & Finkelstein 1994 (traceability) |
| MD-05 | Sizing. Split khi ≥3 change driver / actor độc lập, hoặc tunable từ ≥3 GDD section (kit). Gộp khi mọi change scenario luôn chạm cả hai, hai bên chia một invariant cần update nguyên tử, hoặc mỗi bên đọc state của bên kia ở hầu hết thao tác. Reviewer chạy ≥10 change scenario lấy từ GDD; scenario chạm >2 module = signal (kit). | R | Martin SRP/CCP (*Clean Architecture* ch.7, ch.13); Ford & Richards, *Software Architecture: The Hard Parts* ch.7 |

## B. State & data

| ID | Rule | Check | Nguồn |
|---|---|---|---|
| MD-06 | Single writer: mỗi state item nằm trong `data` của đúng một module; writer khác gửi command cho owner. Giá trị dẫn xuất nhiều nguồn góp → owner + đăng ký contributor. | S! (trùng `data`), R | Parnas 1972; DDD aggregate (Vernon 2011) |
| MD-07 | Save là mechanism: owner của state own field được save và giao phần của mình cho Save; Save không biết schema của feature. | R | Parnas 1972 (module giấu biểu diễn dữ liệu của chính nó); MD-06, MD-13 |
| MD-08 | Mỗi bảng tunable / config của GDD có đúng một owner module. Hình thức lưu (data table, ngoại lệ constant) theo stack rule — Unity: `module-constraints.md` §Hardcoded Content. | R | Martin CCP (*Clean Architecture* ch.13) |
| MD-09 | Contract giữa module mang id / value (save name, currency id), không mang entity type của module khác. | R | Vernon 2011 (reference by identity) |

## C. Dependency & layering

| ID | Rule | Check | Nguồn |
|---|---|---|---|
| MD-10 | Edge = "uses", chiều consumer → owner. `kind`: `call` caller → callee · `event` subscriber → publisher · `data` reader → provider. Mỗi edge cite nhu cầu phía consumer (`source` có quote, hoặc `decision`). Mũi tên trong diagram GDD là ảnh hưởng / luồng dữ liệu — không copy làm dependency; arrow bị đảo / bỏ ghi vào `gddArrows`. | S! (kind, cite, quote), R (chiều) | Bass et al., *Software Architecture in Practice* ch.3 (uses ≠ calls) |
| MD-11 | Không cycle (SCC >1 module). Gỡ theo thứ tự: chuyển responsibility sang module phụ thuộc → tách concept chung xuống thấp → interface ở phía thấp (DIP) → sandwich split → event (chỉ cho fact 1→N không cần reply). | S! | Martin ADP (*Clean Architecture* ch.14); Parnas 1979 |
| MD-12 | Band do architect khai báo; layer của blueprint luôn TÍNH bởi script (không ghi vào blueprint.json): row Foundation theo dep nội bộ Foundation, `Layer k` của band game theo dep game (dep Foundation tính 0). `layer` của modules.json giữ nghĩa topological, do `module-architect` tính theo §Layering rules. | script | `module-architect` §Layering rules |
| MD-13 | Foundation chỉ depend Foundation, engine, package. Foundation → Foundation được phép khi không cycle. | S! (blueprint + modules.json) | Sitecore Helix layers; Unity asmdef referencing |
| MD-14 | Game → game là hợp lệ (chính nó tạo Layer 1..n). Chuỗi dài = signal đẩy concept chung xuống thấp. | R | Helix "feature không depend feature" — KHÔNG áp |
| MD-15 | Module hub (nhiều consumer) chỉ lộ id + abstraction; edge từ module ổn định sang module biến động là signal xem lại (instability I = Ce/(Ca+Ce)). | R | Martin SDP/SAP (*Clean Architecture* ch.14) |
| MD-16 | Composition root (`role: composition`: start-up order, wiring, scene load) ở band game, consume mọi module nó khởi động; chỉ composition root khác (vd app scope → scene scope) được depend nó. Không bao giờ ở Foundation. | S! (`role-placement`) | Boss Room `ApplicationController` + lifetime scope; Unity execution order không đảm bảo |
| MD-17 | Câu kiến trúc của GDD dạng "X không bao giờ gọi Y" / "SDK chỉ gọi trong X" → `forbiddenDeps` / `wraps` kèm quote — vi phạm là blocking. | S! | ArchUnit / matklad ARCHITECTURE.md (invariant là sự vắng mặt) |

## D. Foundation & reuse tag

| ID | Rule | Check | Nguồn |
|---|---|---|---|
| MD-18 | Foundation = tái dùng được ở project khác. Đủ cả 6: (a) secret thuộc platform / quyết định phần mềm, không phải luật game; (b) name, summary, responsibilities, contract label không mang từ vựng domain của GDD (glossary của chương gameplay; tên module không được miễn); (c) deps ⊆ Foundation; (d) không own bảng tunable hay list đặc thù game — list đó thành consumer obligation hoặc module binding band game; (e) không chứa code third-party asset; (f) test được không cần game: core thuần, IO sau port có fake adapter. Tiêu chí phán đoán chưa rõ → decision `foundation`. | (c) S!; (a)(b)(d)(e)(f) R, G | Evans, *DDD Reference* (Generic Subdomain); Unity `constitution.md` (SDK adapter) |
| MD-19 | System của GDD mà định nghĩa mang danh từ game: giữ band game, HOẶC tách mechanism Foundation + module binding band game. Tách là decision `foundation` cho user. | G | Cockburn, Hexagonal Architecture (port vs adapter) |
| MD-20 | Admission ≠ extraction: module Foundation là "candidate" của project cho tới khi project thứ hai dùng. Kit không tạo package / assembly definition. | — | Rule of three (Glass, *Facts and Fallacies* F18); Metz 2016 "The Wrong Abstraction" |
| MD-21 | `buildMode` ≠ `new` cần `extends` = `<path>::<Type>.<Member>` grep-match session này (R3); inventory / audit report chỉ là con trỏ. "Built from" của GDD là claim — code nói khác → decision `gdd-gap`. Adopt package = module `new` làm adapter với `wraps`. | S!, R | `ai-discipline.md` §R3 |

## E. Presentation, event, external, brownfield

| ID | Rule | Check | Nguồn |
|---|---|---|---|
| MD-22 | Presentation là client: screen / presenter nằm ở module `role: presentation` (UI feature home của host); ngoài composition root, không module nào depend nó; nó nghe event / read model và gửi command. | S! (`role-placement`) | Unity `module-constraints.md` §Module Shape; OpenRCT2 `IUiContext` |
| MD-23 | Call khi consumer cần kết quả hoặc đúng một handler hành động. Event chỉ cho fact thì quá khứ, ≥1 subscriber, không reply, payload snapshot, không raise trong handler khác. Một subscriber mà publisher dựa vào = command trá hình. | R | Nystrom, *Game Programming Patterns* "Event Queue"; Fowler 2017 "What do you mean by Event-Driven?" |
| MD-24 | Mỗi SDK / service ngoài được bọc bởi đúng một module; module khác chỉ thấy DTO kết quả. | S! (`wraps` trùng) | Unity `constitution.md` (SDK adapter); DDD Anticorruption Layer |
| MD-25 | Brownfield: mỗi SCC của type graph code hiện có (`ndv_blueprint.py --code-graph`) nằm trọn trong MỘT module shell (`paths` phủ cả SCC) tới khi decision `project` (cite vào SCC) chọn khác. Module khác được `extends` file SCC (bằng chứng concern) nhưng không có `paths` vào đó. Write scope (`paths`) không chồng nhau; module mới nằm ngoài folder code legacy; sửa file legacy là task của module shell. | S! (`scc-split` — `paths` ∪ `extends`, `paths-overlap`); S? (`scc-decided`, `shared-extends-file`) | Fowler StranglerFigApplication, BranchByAbstraction; Feathers, *Working Effectively with Legacy Code* ch.6 |

## Anti-pattern

| Triệu chứng | Rule |
|---|---|
| Một module mỗi bước loop, gọi nhau theo thứ tự loop | MD-02, MD-01 |
| Copy mũi tên diagram GDD làm dependency → cycle giả | MD-10, MD-11 |
| God manager (nhiều lý do đổi, nhiều writer) | MD-05, MD-06 |
| "Layer 0 nghĩa là Foundation"; module chứa tên currency của game ở Foundation | MD-12, MD-18, MD-19 |
| Composition root ở Foundation | MD-16 |
| Gameplay gọi UI | MD-22 |
| State nhiều writer | MD-06 |
| List id của game làm Data row của module Foundation | MD-18(d), MD-19 |
| Folder `Common` / `Utils` | MD-01 (không có secret) |
| Foundation đầu cơ chỉ có một consumer, tách package sớm | MD-20 |
| Type SDK rải nhiều module | MD-24 |
| SCC legacy chia cho nhiều module, write scope chung | MD-25 |
| Event một subscriber thay cho command | MD-23 |
