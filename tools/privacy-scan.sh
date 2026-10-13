#!/usr/bin/env bash
set -euo pipefail

# Gate para impedir que dados de cliente, identificadores reais ou IDs de
# infraestrutura voltem ao repositório público.
patterns=(
  'Rose Portal'
  'roseportaladvocacia\.com\.br'
  'Bruna|Roselaine|Jaqueline|Marli|Adriano'
  '[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}'
  '1OciPZU1|1w8aWx|1kM-Z46|ftctmseyrqhckutpfdeq|ypyuzjczokfrvtndnoem'
)

failed=0
for pattern in "${patterns[@]}"; do
  if git grep -n -I -E -- "$pattern" -- ':!tools/privacy-scan.sh'; then
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "privacy-scan: possíveis dados pessoais/identificadores encontrados" >&2
  exit 1
fi

echo "privacy-scan: OK"
