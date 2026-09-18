# Constitution — core principles

## Context Loading Protocol (NON-NEGOTIABLE)

- Do not read code first.
- Read the project's structure/architecture reference (host rules hoặc register của kit —
  `<matrixRoot>/modules.json`) for project structure và dependencies.
- Read the naming conventions và coding style của stack đang làm.
- When working on a task or implementing, read the pitfalls document (nếu có) to avoid common mistakes.

## Testing policy

Test policy là per-project — host rules define (require / defer / TDD). Khi host KHÔNG define:
default của kit là KHÔNG generate test code trừ khi user explicit yêu cầu.

## Governance

This constitution supersedes conventions documented in comments, READMEs, or informal
agreements. When a conflict exists within the kit ruleset, this document wins (nhưng host
rules vẫn thắng toàn bộ kit — xem [../README.md](../README.md)).

**Amendments** require:

1. A written rationale (why the principle changes).
2. A migration note (what existing code must be updated).

## Writing

- Viết câu cú ngắn gọn, dễ hiểu, vào thẳng vấn đề.
- Update doc không cần log nguyên nhân thay đổi. Change từ A sang B: xóa A ghi B,
  không append B rồi note lý do.
- Implement code không cần comments (code tự nói); comment chỉ khi diễn tả constraint
  mà code không thể hiện được.
