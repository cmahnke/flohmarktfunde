#!/bin/sh

RUN_DEPENDENCIES="bash coreutils imagemagick"

echo "Installing $RUN_DEPENDENCIES"
sudo apt-get install $RUN_DEPENDENCIES
