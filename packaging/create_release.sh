#!/usr/bin/env bash

# get packaging dir
SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

echo "building the packages..."

SKB_VERSION=$( $SCRIPT_DIR/tools/get-skb-version.sh )
echo "Skybase version: $SKB_VERSION"
