#!/bin/bash

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <prefix> <directory>"
    exit 1
fi

PREFIX="$1"
DIR="$2"

if [ ! -d "$DIR" ]; then
    echo "Error: '$DIR' is not a directory"
    exit 1
fi

find "$DIR" -type f | while read -r filepath; do
    dir=$(dirname "$filepath")
    filename=$(basename "$filepath")
    newpath="$dir/${PREFIX}${filename}"

    if [ "$filepath" != "$newpath" ]; then
        mv "$filepath" "$newpath"
        echo "Renamed: $filepath -> $newpath"
    fi
done
