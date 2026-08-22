#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")" && pwd)"
data_home="${XDG_DATA_HOME:-${HOME}/.local/share}"
bin_home="${HOME}/.local/bin"
venv="${data_home}/omarchy-markets/venv"
mcp="${HOME}/Projects/coinbase-portfolio-mcp"

python -m venv --system-site-packages "${venv}"
"${venv}/bin/python" -m pip install --quiet --upgrade pip
"${venv}/bin/python" -m pip install --quiet --upgrade "${root}"
if [[ -d $mcp ]]; then
  "${venv}/bin/python" -m pip install --quiet --upgrade "${mcp}"
fi
mkdir -p "${bin_home}" "${HOME}/.config/coinbase-mcp"
ln -sfn "${venv}/bin/omarchy-markets" "${bin_home}/omarchy-markets"
"${bin_home}/omarchy-markets" install

echo "Ready. Quotes: omarchy-markets status"
echo "Portfolio needs ~/.config/coinbase-mcp/api_key and api_secret"
