#!/usr/bin/env bash
# ============================================================
# PriceOracle-AVS  —  one-shot dev environment installer
#
# Run inside WSL2 Ubuntu 22.04 (or any Ubuntu 22.04 box):
#
#   bash setup_dev.sh
#
# This installs everything you need for the Layr-Labs/incredible-
# squaring-avs fork: Go 1.21, Foundry (forge / cast / anvil),
# Docker, plus a few CLI conveniences. Idempotent — safe to re-run.
# ============================================================

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
say() { echo -e "${GREEN}==>${NC} $*"; }
warn() { echo -e "${YELLOW}!!${NC} $*"; }
die()  { echo -e "${RED}xx${NC} $*" >&2; exit 1; }

# --- 0. sanity checks -----------------------------------------------------

if [[ "$(uname)" != "Linux" ]]; then
  die "This script targets Linux (use WSL2 on Windows)."
fi

if [[ $EUID -eq 0 ]]; then
  warn "Running as root. That's OK in WSL but unusual elsewhere."
fi

# --- 1. apt deps ----------------------------------------------------------

say "Updating apt and installing base packages…"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  build-essential git curl wget make jq unzip ca-certificates \
  pkg-config libssl-dev libusb-1.0-0-dev

# --- 2. Go 1.21 -----------------------------------------------------------

GO_VERSION="1.21.5"
if command -v go >/dev/null 2>&1 && go version | grep -q "$GO_VERSION"; then
  say "Go $GO_VERSION already installed."
else
  say "Installing Go $GO_VERSION…"
  wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tgz
  sudo rm -rf /usr/local/go
  sudo tar -C /usr/local -xzf /tmp/go.tgz
  rm /tmp/go.tgz
  if ! grep -q '/usr/local/go/bin' "$HOME/.bashrc"; then
    echo 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin' >> "$HOME/.bashrc"
  fi
fi
export PATH="$PATH:/usr/local/go/bin:$HOME/go/bin"
go version

# --- 3. Foundry -----------------------------------------------------------

if command -v forge >/dev/null 2>&1; then
  say "Foundry already installed: $(forge --version | head -1)"
else
  say "Installing Foundry…"
  curl -sL https://foundry.paradigm.xyz | bash
  # foundryup is dropped in ~/.foundry/bin
  export PATH="$PATH:$HOME/.foundry/bin"
  foundryup
fi
forge --version

# --- 4. Docker (needed for Prometheus side-car & some integration tests) --

if command -v docker >/dev/null 2>&1; then
  say "Docker already installed."
else
  say "Installing Docker…"
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" || true
  warn "You will need to log out and back in (or run 'newgrp docker') for the docker group to take effect."
fi
docker --version || true

# --- 5. summary -----------------------------------------------------------

cat <<EOF

========================================================
 ${GREEN}DONE${NC}.  Installed:
  - go        $(go version 2>/dev/null | awk '{print $3}' || echo missing)
  - forge     $(forge --version 2>/dev/null | head -1 || echo missing)
  - cast      $(cast --version 2>/dev/null | head -1 || echo missing)
  - anvil     $(anvil --version 2>/dev/null | head -1 || echo missing)
  - docker    $(docker --version 2>/dev/null || echo missing)

 Next:
   1. Re-source your shell:    source ~/.bashrc
   2. Fork the repo on GitHub: https://github.com/Layr-Labs/incredible-squaring-avs
   3. Clone into ~/6883/PriceOracle-AVS and run:
        make build-contracts
        make start-anvil-chain-with-el-and-avs-deployed
      (then in a 2nd terminal: make start-aggregator
       then in a 3rd terminal: make start-operator)
========================================================
EOF
