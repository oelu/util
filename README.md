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

### httpproxy.py

MITM proxy for HTTP troubleshooting using the mitmproxy library.

**Dependencies:** `pip install mitmproxy` (and `cryptography` for CA generation)

```bash
./httpproxy.py [--verbose] [--port PORT]
./httpproxy.py --tls-inspection --ca-pem ca.pem
./httpproxy.py --generate-tls-ca
```

**Options:**
- `--verbose, -v` - Log full HTTP headers, request and response
- `--tls-inspection` - Enable TLS inspection (default: tunnel mode)
- `--ca-pem FILE` - Combined CA cert+key PEM file
- `--ca-cert FILE` - CA certificate for TLS inspection
- `--ca-key FILE` - CA private key for TLS inspection
- `--generate-tls-ca` - Generate CA files (ca.crt, ca.key, ca.pem)
- `--ca-cn NAME` - Common Name for generated CA (default: MITM Proxy Root CA)
- `--ca-org NAME` - Organization for generated CA (default: MITM Proxy CA)
- `--port, -p PORT` - Proxy port (default: 8080)

**Note:** Verbose logging for HTTPS requires `--tls-inspection`. Without it, HTTPS traffic is tunneled opaquely and cannot be inspected.

**Example:**
```bash
# Generate CA for TLS inspection
./httpproxy.py --generate-tls-ca

# Run proxy with verbose logging (HTTP only without TLS inspection)
./httpproxy.py --verbose

# Run with TLS inspection for HTTPS verbose logging
./httpproxy.py --tls-inspection --ca-pem ca.pem -v
```

**Testing with curl:**
```bash
# HTTP proxy
curl -x http://localhost:8080 http://example.com

# HTTPS proxy (tunnel mode, no inspection)
curl -x http://localhost:8080 https://example.com

# HTTPS with TLS inspection (skip cert verify)
curl -x http://localhost:8080 -k https://example.com

# HTTPS with TLS inspection (trust CA)
curl -x http://localhost:8080 --cacert ca.crt https://example.com
```

### markdown-toc.py

Generates and inserts a table of contents into markdown files. Inserts TOC after the first heading, wrapped in `<!-- TOC -->` markers for idempotent re-runs.

```bash
./markdown-toc.py <file.md> [options]
```

**Options:**
- `-o, --output FILE` - Write to FILE instead of modifying in-place
- `-l, --levels N` - Max heading depth to include (default: 3)
- `--stdout` - Print result to stdout instead of modifying file
- `--include-first` - Include first heading in TOC

**Example:**
```bash
./markdown-toc.py README.md              # Modify in-place
./markdown-toc.py README.md --stdout     # Print to stdout
./markdown-toc.py README.md -l 2         # Only include h1 and h2
```
