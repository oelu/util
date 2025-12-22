# util

A collection of utility scripts.

## Scripts

### prefix-files.sh

Adds a prefix to all files in a directory and its subdirectories.

```bash
./prefix-files.sh <prefix> <directory>
```

**Example:**
```bash
./prefix-files.sh backup_ ./photos
# Renames photo.jpg -> backup_photo.jpg
```

### rename-files-spaces.sh

Replaces spaces with underscores in file and folder names. Runs in interactive mode by default.

```bash
./rename-files-spaces.sh [-y|--yes|--non-interactive] <directory>
```

**Options:**
- `-y, --yes` - Auto-confirm all renames (shows each rename)
- `--non-interactive` - Rename silently without prompts

**Example:**
```bash
./rename-files-spaces.sh ./documents
# Interactive: asks before renaming "My File.txt" -> "My_File.txt"

./rename-files-spaces.sh -y ./documents
# Auto-confirms all renames, showing each one

./rename-files-spaces.sh --non-interactive ./documents
# Renames all files/folders with spaces silently
```
