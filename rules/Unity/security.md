---
paths:
  - "**/*.cs"
  - "**/*.csx"
---

# Unity Security

> Extends [../Shared/security.md](../Shared/security.md). Đây là SoT trust boundary
> client↔server — áp dụng khi project là server-authoritative (kiểm tra host architecture
> decision; project offline/single-player bỏ qua §Trust boundary).

## Trust boundary

- Client KHÔNG quyết định kết quả gameplay (currency, RNG, damage, drop, pity, cap) — chỉ
  gửi action intent và render payload server trả về.
- Không lưu state quyết định reward/progress ở client (PlayerPrefs/local) như authoritative.
- Client simulation chỉ là prediction/render — server re-simulate là ground truth và
  validate mọi kết quả client claim.
- RNG seed server-minted, per-battle/per-run/per-pull, KHÔNG expose client; replay dựng lại
  từ action log + seed lưu server.
- State quyết reward/progress (pity, mileage, daily counter, cap, stamina anchor) giữ
  server-side là SoT.
- Mọi currency mutation qua server validation; client balance reflect từ response, không tự
  cộng/trừ local.
- Mechanic authoritative ghi server-side audit log ngay tại mutation (currency, IAP grant,
  pity, drop, craft, purchase, conversion, unequip).
- Contract phản ánh trust boundary: request mang INTENT (action+target; delta+reason_code+
  ref_id), response mang RESULT + transaction/log id; server KHÔNG nhận pre-computed result
  từ client.

## Input validation

- Validate data tại boundary trước khi dùng: API response, user input, file save, config
  JSON — không trust external data.
- Guard clause + fail fast với message rõ ràng ([../Shared/coding-style.md](../Shared/coding-style.md)).

## Logging & error

- Không log raw token, password, PII. Log format theo [constitution.md](constitution.md).
- Lỗi hiển thị cho player đi qua hệ notification/toast dùng chung của project
  ([known-pitfalls.md](known-pitfalls.md)); message an toàn, không leak chi tiết hệ thống
  (stack trace, path, nội dung request).

## Secret defaults

- Không hardcode secret/token/password thật trong source ([../Shared/security.md](../Shared/security.md)).
- CARVE-OUT: một PUBLIC well-known dev default của SDK third-party đặt làm `[SerializeField]`
  default cho localhost/dev, overridable qua Inspector/SO asset, KHÔNG phải finding
  hardcoded-secret — vì không phải secret (công khai) và env-configurable. Secret/token thật
  vẫn cấm hardcode.
