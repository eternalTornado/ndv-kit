#!/usr/bin/env bash
# ndvkit check-deps — fail when code under a folder references a namespace it must not use.
# Rules: <ndvRoot>/deps.rules, one per line: "<folder> <forbidden namespace>"; '#' starts a comment.
# Run from the repo root. Exit 0 = clean or no rules, 1 = violations, 2 = bad rules file.
root="${NDV_ROOT:-.ndv}"
rules="$root/deps.rules"
if [ ! -f "$rules" ]; then
  echo "check-deps: no $rules — skipped"
  exit 0
fi
fail=0; n=0
while read -r dir ns rest; do
  case "$dir" in ''|\#*) continue ;; esac
  if [ -z "$ns" ] || [ -n "$rest" ]; then
    echo "check-deps: bad line in $rules: $dir $ns $rest"; exit 2
  fi
  n=$((n+1))
  [ -d "$dir" ] || { echo "check-deps: folder not found, rule skipped: $dir"; continue; }
  esc=$(printf '%s' "$ns" | sed 's/\./\\./g')
  hits=$(grep -rnE --include='*.cs' "(^|[^A-Za-z0-9_.])$esc([.;[:space:]]|$)" "$dir" \
         | grep -vE '^[^:]+:[0-9]+:[[:space:]]*(//|\*|/\*)' \
         | grep -vE '^[^:]+:[0-9]+:[[:space:]]*namespace[[:space:]]')
  if [ -n "$hits" ]; then
    echo "✗ $dir must not use $ns:"
    printf '%s\n' "$hits" | sed 's/^/    /'
    fail=1
  fi
done < "$rules"
[ "$fail" -eq 0 ] && echo "check-deps: $n rule(s), no violation"
exit "$fail"
