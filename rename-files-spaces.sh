#!/bin/bash

set -e

INTERACTIVE=true
AUTO_YES=false
DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --non-interactive)
            INTERACTIVE=false
            shift
            ;;
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [-y|--yes|--non-interactive] <directory>"
            echo "Replaces spaces with underscores in file and folder names."
            echo ""
            echo "Options:"
            echo "  -y, --yes          Auto-confirm all renames (shows each rename)"
            echo "  --non-interactive  Rename silently without prompts"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        -*)
            echo "Error: Unknown option '$1'"
            echo "Usage: $0 [-y|--yes|--non-interactive] <directory>"
            exit 1
            ;;
        *)
            DIR="$1"
            shift
            ;;
    esac
done

if [ -z "$DIR" ]; then
    echo "Usage: $0 [-y|--yes|--non-interactive] <directory>"
    exit 1
fi

if [ ! -d "$DIR" ]; then
    echo "Error: '$DIR' is not a directory"
    exit 1
fi

# Use -depth to process contents before their parent directories
find "$DIR" -depth -name "* *" | while read -r filepath; do
    parent=$(dirname "$filepath")
    oldname=$(basename "$filepath")
    newname="${oldname// /_}"
    newpath="$parent/$newname"

    if [ "$filepath" != "$newpath" ]; then
        if [ "$INTERACTIVE" = true ]; then
            echo "Rename: $filepath"
            echo "    ->  $newpath"
            if [ "$AUTO_YES" = true ]; then
                mv "$filepath" "$newpath"
                echo "Renamed."
            else
                read -r -p "Proceed? [y/N] " response < /dev/tty
                case "$response" in
                    [yY][eE][sS]|[yY])
                        mv "$filepath" "$newpath"
                        echo "Renamed."
                        ;;
                    *)
                        echo "Skipped."
                        ;;
                esac
            fi
            echo ""
        else
            mv "$filepath" "$newpath"
            echo "Renamed: $filepath -> $newpath"
        fi
    fi
done
