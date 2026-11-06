---
name: ndv-impact
description: "GDD đổi → bảng tác động. Diff GDD từ <ndvRoot>/gdd-ref, map từng thay đổi về module của blueprint, phân loại (text · value · behavior · new · structural) và tier S/M/L, user duyệt bảng, rồi từng dòng chạy qua /ndv-blueprint --update hoặc /ndv-brief. Xong hết dòng → cập nhật gdd-ref."
argument-hint: "[--base <commit>]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Task, AskUserQuestion
---

Config: `.claude/ndvkit/ndvkit.config.json` → `gddRoot`, `ndvRoot` (vắng → `.ndv`). Template:
`.claude/ndvkit/templates/impact-template.md`.

## 0. Đang có bảng mở?

File mới nhất trong `<ndvRoot>/impact/` còn dòng `pending` → không tạo bảng mới: báo trạng thái từng
dòng, đề xuất dòng `pending` kế tiếp (Tiếp theo bên dưới). Mọi dòng `done`/`deferred`/`skipped` →
**đóng vòng**: ghi `git log -1 --format=%H -- <gddRoot>` vào `<ndvRoot>/gdd-ref`, báo "Đồng bộ GDD
xong"; dòng `deferred` được nhắc lại ở lần chạy sau.

## 1. Diff

- `base` = `--base`, else `<ndvRoot>/gdd-ref`. Không có → `AskUserQuestion`: commit lần cuối
  `blueprint.json` được approve (`git log -1 --format=%H -- <ndvRoot>/blueprint.json`) / nhập commit
  (Other) / coi như vừa đồng bộ (ghi gdd-ref = commit GDD hiện tại, dừng).
- `git diff <base> -- <gddRoot>` + file GDD chưa track (`git ls-files -o --exclude-standard`).
  Trống → "GDD không đổi kể từ <base>", dừng.
- Diff dài: spawn `Explore` để tóm từng hunk thành (file#heading, cũ → mới); không kéo cả diff vào
  main context.

## 2. Bảng tác động

Mỗi thay đổi có nghĩa → một dòng `I-<n>`:

- **Module:** map `file#heading` về module có `sources` / `loops` cite heading đó trong
  `<ndvRoot>/blueprint.json`. Không module nào cite → module `—`, loại thường là `new`.
- **Loại → tier:** `text` (không ảnh hưởng gameplay) → `—` · `value` (chỉ đổi số) → S · `behavior`
  (đổi hành vi trong một module) → M · `new` (feature/system mới) → M hoặc L, kèm cập nhật blueprint ·
  `structural` (ranh giới module, dependency, bỏ feature) → `/ndv-blueprint --update` rồi L.
- **Việc:** một dòng, động từ.
- Feature L đang dở (`<ndvRoot>/*/progress.md` có Current) mà dòng chạm module của milestone hiện tại
  hoặc sau → ghi vào "Ảnh hưởng tới feature đang làm": cần `/ndv-brief <feature> --replan`.

Ghi `<ndvRoot>/impact/<yyyy-mm-dd>.md` theo template, mọi dòng `pending`.

## 3. Duyệt

Tóm tắt bảng trong chat. `AskUserQuestion`: Approve hết / chọn dòng làm sau (Other: "defer I-2, I-5")
/ sửa phân loại (Other). Ghi lại `deferred`/`skipped` và `Approved: <date>`. Đây là chỗ sửa hiểu sai
rẻ nhất — trước khi có dòng code nào.

## Tiếp theo (một dòng)

- Có dòng `structural` hoặc `new` cần module mới → `/ndv-blueprint --update`.
- Có feature cần replan → `/ndv-brief <feature> --replan "GDD I-<n>"`.
- Dòng `pending` kế tiếp: S → làm thẳng "I-<n>: <việc>" (Stop hook ép verify) · M → `/ndv-brief "I-<n>:
  <việc>"` · L → `/ndv-brief <feature> --L`.
- Không còn dòng `pending` → `/ndv-impact` để đóng vòng.
