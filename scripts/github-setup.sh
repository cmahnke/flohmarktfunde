#!/usr/bin/env bash

set -e -o pipefail

RUN_DEPENDENCIES="bash coreutils imagemagick"

echo "Installing $RUN_DEPENDENCIES"
sudo apt-get install $RUN_DEPENDENCIES
