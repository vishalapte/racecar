#!/usr/bin/env bash
# Install system dependencies that cannot be pip-installed.
# Idempotent: checks presence before installing.
# Called by `make system-deps` (which `make install` depends on).
set -euo pipefail

install_claude() {
    if command -v claude >/dev/null 2>&1; then
        echo "claude present ($(command -v claude))"
    else
        if ! command -v curl >/dev/null 2>&1; then
            echo "ERROR: curl required to install claude CLI. Install curl and re-run." >&2
            exit 1
        fi
        echo "→ curl -fsSL https://claude.ai/install.sh | bash"
        curl -fsSL https://claude.ai/install.sh | bash
    fi
}

install_package() {
    local cmd=$1 brew_pkg=$2 apt_pkg=$3
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "$cmd present ($(command -v "$cmd"))"
        return
    fi
    case "$(uname -s)" in
        Darwin)
            if ! command -v brew >/dev/null 2>&1; then
                echo "ERROR: Homebrew required but not found. Install from https://brew.sh" >&2
                exit 1
            fi
            echo "→ brew install $brew_pkg"
            brew install "$brew_pkg"
            ;;
        Linux)
            echo "→ apt-get install -y $apt_pkg"
            apt-get install -y "$apt_pkg"
            ;;
        *)
            echo "WARNING: unsupported platform $(uname -s); install $apt_pkg manually" >&2
            ;;
    esac
}

# install_package soffice libreoffice libreoffice
install_claude
