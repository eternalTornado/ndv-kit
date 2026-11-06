#!/usr/bin/env bash
# ndvkit Stop hook — block finishing while .cs files changed after the last /ndv-verify.
# Exit 2 sends the message back to the agent so it verifies and fixes before stopping.
# A second stop in the same chain (stop_hook_active) always passes, so it never loops.
input=$(cat)
printf '%s' "$input" | grep -q '"stop_hook_active"[[:space:]]*:[[:space:]]*true' && exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

root="${NDV_ROOT:-.ndv}"
stamp="$root/verified.stamp"

changed=$( { git diff --name-only --diff-filter=d HEAD -- '*.cs' 2>/dev/null || git diff --name-only --diff-filter=d -- '*.cs'
             git ls-files -o --exclude-standard -- '*.cs'; } | sort -u )
[ -z "$changed" ] && exit 0

if [ -f "$stamp" ]; then
  stale=0
  while IFS= read -r f; do
    [ -f "$f" ] && [ "$f" -nt "$stamp" ] && { stale=1; break; }
  done <<EOF_LIST
$changed
EOF_LIST
  [ "$stale" -eq 0 ] && exit 0
fi

count=$(printf '%s\n' "$changed" | wc -l | tr -d ' ')
echo "ndvkit: $count file .cs đã đổi sau lần verify cuối. Chạy /ndv-verify (compile + deps + test) và sửa tới khi xanh rồi mới kết thúc." >&2
exit 2
