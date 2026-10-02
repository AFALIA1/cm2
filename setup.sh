#!/usr/bin/env bash
# Kept for backward compatibility — install.sh handles Linux and macOS.
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install.sh" "$@"
