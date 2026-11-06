#!/usr/bin/env bash
# ndvkit SessionStart hook — remind when the GDD changed since the last sync (<ndvRoot>/gdd-ref).
# Prints one line into the session context; never blocks.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
root="${NDV_ROOT:-.ndv}"
[ -f "$root/gdd-ref" ] || exit 0
ref=$(tr -d ' \n\r' < "$root/gdd-ref")
cfg=".claude/ndvkit/ndvkit.config.json"
gdd=$(sed -n 's/.*"gddRoot"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$cfg" 2>/dev/null | head -1)
[ -n "$gdd" ] && [ -d "$gdd" ] || exit 0
git cat-file -e "$ref^{commit}" 2>/dev/null || { echo "ndvkit: gdd-ref $ref không còn trong git — chạy /ndv-impact để đặt lại mốc."; exit 0; }
if ! git diff --quiet "$ref" -- "$gdd" 2>/dev/null || [ -n "$(git ls-files -o --exclude-standard -- "$gdd")" ]; then
  n=$( { git diff --name-only "$ref" -- "$gdd"; git ls-files -o --exclude-standard -- "$gdd"; } | sort -u | wc -l | tr -d ' ')
  echo "ndvkit: GDD đã đổi ($n file) kể từ lần đồng bộ cuối (${ref:0:7}). Đề xuất: /ndv-impact"
fi
exit 0
