# Id plan — allocation invariants

> File này giữ INVARIANT về id allocation. Bảng range/giá trị CỤ THỂ là per-project —
> define trong host rules; pipeline cite bảng đó khi cấp id mới.

## Golden rule

1 entity = 1 global-unique INT `config_id`; cùng số đó dùng cho PK config, FK player-state,
asset folder, addressables/bundle address, JSON `id`. String KHÔNG bao giờ là key — chỉ là
cột `code` UNIQUE (traceability về design doc). Id đã cấp là immutable — không renumber/reuse.

## Range design rules

- Mỗi concept (currency, material, hero, skill, equipment…) có MỘT range riêng với LENGTH
  cố định; hai range được phép cùng leading digit chỉ khi khác length.
- Ký hiệu format digit-position (vd `1rrdddd` = concept 1, rarity 2 digit, seq 4 digit) chỉ
  là cách ĐỌC — giá trị lưu luôn là INT phẳng.
- Sub-range cấp theo family/decade (vd 40001–40009 family A, 40011–40019 family B); family
  mới lấy decade trống kế tiếp.
- Cấp range/family mới hoặc đổi cấu trúc = owner decision, ghi lại được trace. Range dùng
  quá ~80% phải mở discussion mở rộng trước khi cạn.

## Namespace tách biệt

**CONFIG id namespace** (content/entity) và **runtime key namespace** (vd stat key cho
`GetStat(statId)`) là hai không gian RIÊNG — được phép trùng số vì lookup hoàn toàn khác
nhau. Không coi trùng số cross-namespace là conflict; không "fix" bằng renumber.

## Composite key client-only

Row key tổng hợp cho lookup/curve table (vd `entityId * 10 + tier`) là key nội bộ của
data-table layer, KHÔNG phải config_id — phải nằm ngoài mọi config range (khác length),
và phải guard biên của thành phần nhân (vd `tier ≤ 9` khi multiplier `*10`).

## Wire & cross-tier

Một datum đi qua nhiều tier giữ nguyên id INT; string legacy (nếu có) chỉ là cột `code`
deprecated — mọi lookup runtime theo INT id, không theo string.
