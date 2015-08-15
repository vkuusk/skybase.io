#!/usr/bin/env bash

# get tools directory
SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

# relative loaction of the file with version
REL_PATH="../../skybase/__init__.py"

SKB_VERSION=$(awk '/__version__/{gsub(/\047/,""); print $3}' $SCRIPT_DIR/$REL_PATH)

echo $SKB_VERSION
