# AI Discipline — worker core (R1–R5, R7)

> **Canonical SSoT** cho AI behavior rules trong project áp dụng bộ này. Mọi rule file /
> skill khác **cite-back** về đây thay vì restate. NON-NEGOTIABLE, áp dụng cho mọi AI agent
> (main session, sub-agents, scheduled agents). Skill cite `§R-NN` được hiểu là cite về bộ này.
>
> File này là phần MỌI worker (sub-agent ghi artifact / code / report) phải đọc. R6, R8, R9,
> R10 + Exception / Enforcement / Governance sống ở
> [ai-discipline-session.md](ai-discipline-session.md) — main session / orchestrator đọc,
> worker không cần.

---

## R1 — Tool-first, verify before claim

Trước khi khẳng định bất kỳ điều gì về file / API / config / state: dùng tool (Read / Grep /
Glob / Bash) verify trước. Sau khi edit / run: confirm exit code + output trước khi nói "done".
Không trả lời từ memory.

**Format cite**: doc/artifact (GDD, spec, rules) → `<path>#<section>` hoặc `<path>:<line>`;
code (file dưới `codeRoots`) → `<path>::<Type>.<Member>` (symbol-based, mặc định) — `:<line>`
chỉ đi kèm SAU symbol khi cần chỉ đúng một dòng (`<path>::<Type>.<Member>:<line>`), không bao
giờ đứng một mình cho code; rule file → đúng đường dẫn của file đã mở, ưu tiên `#<section>` hơn
`:<line>` (`<kitRulesRoot>/<Nhóm>/<file>.md#<section>` cho kit default rules; `<rulesRoot>/…`
chỉ khi file thật sự nằm đó) — tên ngắn `Unity/…`, `Shared/…`, `Server/…` trong rules là đường
dẫn tương đối so với root của bộ rules chứa nó, không ghép với `<rulesRoot>`; web → kèm `#anchor`
hoặc literal quote ≤2 câu. Symbol phải grep match trong file tại thời điểm ghi.

**Audit Evidence carve-out**: report của `/ndv-audit-code` là snapshot tại một commit
(frontmatter `git`). Evidence dùng `<path>::<Type>.<Member>:<line>` cho file có symbol;
`<path>:<line>` + literal quote cho file không có symbol (markup, stylesheet, data, asset).
Fixer verify bằng literal quote, không bằng line — quote lệch → `stale`.

**BANNED**:

- Cite từ memory ("tôi nhớ là file có…")
- Cite vì "về chủ đề" thay vì "chứa nội dung"
- Root URL khi content nằm sub-section
- Section number không kèm tên
- Path chưa verify tồn tại
- Cite code bằng `<path>:<line>` không kèm symbol ngoài audit carve-out ở trên (line-only anchor vỡ khi code dịch dòng)

> Link đúng **nội dung**, không link đúng **chủ đề**.

---

## R2 — Say "I don't know"

Source thiếu info → 1 trong 3 lựa chọn hợp lệ:

1. Inline `NEEDS CLARIFICATION: <câu hỏi cụ thể>` tại vị trí thiếu rồi STOP, không fill quanh nó
2. Hỏi user nếu đang active
3. `N/A — <lý do cụ thể>` cho field optional

**BANNED**: `TBD`, `see plan`, `to be defined`, `coming soon`, đoán từ filename, suy luận từ
"typical X game", lorem ipsum, copy header để rỗng body bên dưới.

Thừa nhận không biết là output hợp lệ; bịa là vi phạm.

---

## R3 — Cite every claim

Mọi fact / value / decision phải kèm: `<path>#<section>` (doc) hoặc `<path>::<Type>.<Member>`
(code, theo R1), grep output, web `URL#anchor`, hoặc literal quote ≤2 câu. Phải đã read / grep
location đó trong session hiện tại.

Cite vào code: symbol phải grep-match trong file tại thời điểm ghi artifact. Anchor code kế
thừa từ artifact thượng nguồn (requirement, specify, modules.json, audit report) mà chưa mở lại
file trong session này KHÔNG được ghi làm cite của artifact hiện tại — đổi sang symbol đã
verify, hoặc bỏ anchor và giữ claim ở dạng không cite code.

**Quyết định của user / owner** (câu trả lời AskUserQuestion khi resolve `NEEDS CLARIFICATION`,
triage, chọn phương án) là source hợp lệ khi artifact thượng nguồn im lặng:
`decision: <yyyy-mm-dd> — "<literal answer ≤2 câu>"`. Form này không dùng để ghi đè literal đã
có ở GDD — câu trả lời mâu thuẫn thượng nguồn thì sửa thượng nguồn trước, artifact hạ
nguồn cite thượng nguồn.

**Cite content, không cite topic.**

**Example xấu**: "Theo rules thì hệ thống phải server-authority" (không cite section, không quote).

---

## R4 — Literal quote khi adopt source

Khi chuyển nội dung từ source (GDD / manifest / contracts / framework doc) sang artifact,
MUST quote literal cho:

- Balance constants, numeric thresholds, percentages
- Formula (đầy đủ ký hiệu, không paraphrase)
- Enum value, error code
- API field name / type / constraint
- Permission codename, URL pattern, regex
- Edge case condition (boundary, invalid input)
- ID list

Paraphrase chỉ OK cho prose overview / narrative transition. Quote MUST kèm cite
`<path>#<section>` hoặc `<path>:<line>`.

Quote chứa anchor code của nguồn (vd một câu GDD có `Foo.cs:23-37`): giữ nguyên trong quote
vì đó là văn bản nguồn, nhưng anchor đó KHÔNG tính là cite của artifact hiện tại. Artifact cần
cite code cho cùng claim → cite riêng theo R3 (symbol, đã mở file).

---

## R5 — No AI-invented content trong artifact

Cấm trong spec / plan / tasks / audit / ADR / PR / commit / review (trừ khi user explicit
yêu cầu hoặc source được cite inline):

- Timeline / deadline / effort estimate
- Process workflow tự bịa nếu skill không define
- Ranked "Top N" findings (chỉ list phẳng theo ID)
- Recommendation không có cite
- New severity / verdict / pattern tự bịa
- Dependency / execution order không có trong design / lead decision
- Effort / cost / risk score tự gán

**Banned phrase**: `~Xmin`, `approximately`, `should take`, `khoảng X phút`, `Top-3`,
`Tier-1/2/3` (nếu không cite skill define).

**Banned ambiguous quantifier** (SoT — trừ khi kèm số cụ thể + cite): `vài`, `nhiều`,
`khoảng`, `chừng`, `hơi`, `khá`, `tương đối`, `một số` — thay bằng số cụ thể + cite, hoặc
`N/A — không đo được trong session này`.

**OK**: Observed duration từ tool output cite literal; số cite từ source.

Conversational recommendation trong chat OK; ghi vào artifact file chỉ khi user explicit yêu cầu lưu.

---

## R7 — Research / report artifact: Finding + Evidence + Impact

Mọi finding trong research / audit / analysis artifact phải có 3 phần:

1. **Finding**: vấn đề / data point (1 câu)
2. **Evidence**: source cite (`<path>#<section>` / `<path>::<Symbol>[:<line>]` / `<URL>#anchor` / grep output) + literal quote ≤2 câu
3. **Impact**: 1 câu giải thích relevance / hậu quả

**Severity** (tập đóng, SoT tại đây): `blocker · critical · high · medium · low · info`.
Guide (điều kiện nào rơi vào mức nào) sống trong agent `code-auditor`; không mint mức mới,
không viết hoa biến thể.

**BANNED**:

- Finding không quote (path-only)
- Paraphrase thay literal
- Web cite chỉ root URL
- Summary "X có vấn đề Y" không cite finding cụ thể
- "Có thể có vấn đề về performance" không cite benchmark / line
