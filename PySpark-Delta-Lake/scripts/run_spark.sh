#!/usr/bin/env bash
set -euo pipefail

if [ -d "/usr/local/opt/openjdk@17" ]; then
  export JAVA_HOME="/usr/local/opt/openjdk@17"
  export PATH="$JAVA_HOME/bin:$PATH"
elif [ -d "/opt/homebrew/opt/openjdk@17" ]; then
  export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
  export PATH="$JAVA_HOME/bin:$PATH"
fi

exec .venv/bin/python "$@"
