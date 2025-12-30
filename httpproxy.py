#!/usr/bin/env python3
"""
MITM Proxy for HTTP troubleshooting using mitmproxy library.

Usage:
    httpproxy.py [--verbose] [--port PORT]
    httpproxy.py --tls-inspection --ca-pem ca.pem
    httpproxy.py --generate-tls-ca

Requires: pip install mitmproxy
"""

from __future__ import annotations

import argparse
import atexit
import datetime
import logging
import os
import signal
import sys
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mitmproxy import http

try:
    from mitmproxy import options
    from mitmproxy.tools.dump import DumpMaster
    HAS_MITMPROXY = True
except ImportError:
    HAS_MITMPROXY = False

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Track temp files for cleanup
_temp_files: list[str] = []


def _cleanup_temp_files() -> None:
    """Clean up temporary files on exit."""
    for fpath in _temp_files:
        try:
            if os.path.exists(fpath):
                os.unlink(fpath)
                logger.debug("Cleaned up temp file: %s", fpath)
        except OSError:
            pass


atexit.register(_cleanup_temp_files)


def generate_ca(
    common_name: str = "MITM Proxy Root CA",
    organization: str = "MITM Proxy CA",
    validity_days: int = 3650,
) -> None:
    """Generate a CA certificate and private key."""
    if not HAS_CRYPTOGRAPHY:
        logger.error("'cryptography' package required for CA generation")
        logger.error("Install with: pip install cryptography")
        sys.exit(1)

    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=validity_days))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    key_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    cert_bytes = cert.public_bytes(serialization.Encoding.PEM)

    # Set restrictive umask before creating files to avoid race condition
    old_umask = os.umask(0o077)
    try:
        with open("ca.key", "wb") as f:
            f.write(key_bytes)

        with open("ca.crt", "wb") as f:
            f.write(cert_bytes)

        # Combined PEM for mitmproxy
        with open("ca.pem", "wb") as f:
            f.write(key_bytes)
            f.write(cert_bytes)
    finally:
        os.umask(old_umask)

    logger.info("Generated:")
    logger.info("  ca.crt - CA certificate (import into browser/system)")
    logger.info("  ca.key - CA private key")
    logger.info("  ca.pem - Combined cert+key for mitmproxy")


class VerboseLogger:
    """Addon to log full HTTP request/response details."""

    def request(self, flow: http.HTTPFlow) -> None:
        req = flow.request
        logger.info("=" * 60)
        logger.info(">>> REQUEST: %s %s", req.method, req.pretty_url)
        logger.info("-" * 40)
        for name, value in req.headers.items():
            logger.info("  %s: %s", name, value)
        if req.content:
            logger.info("-" * 40)
            logger.info("  Body (%d bytes):", len(req.content))
            try:
                text = req.content.decode("utf-8", errors="replace")[:2000]
                logger.info("  %s", text)
            except (UnicodeDecodeError, AttributeError):
                logger.info("  [Binary data]")

    def response(self, flow: http.HTTPFlow) -> None:
        resp = flow.response
        if resp is None:
            return
        logger.info("-" * 40)
        logger.info("<<< RESPONSE: %d %s", resp.status_code, resp.reason)
        logger.info("-" * 40)
        for name, value in resp.headers.items():
            logger.info("  %s: %s", name, value)
        if resp.content:
            logger.info("-" * 40)
            logger.info("  Body (%d bytes):", len(resp.content))
            try:
                text = resp.content.decode("utf-8", errors="replace")[:2000]
                logger.info("  %s", text)
            except (UnicodeDecodeError, AttributeError):
                logger.info("  [Binary data]")
        logger.info("=" * 60)


async def run_proxy(args: argparse.Namespace) -> None:
    """Run the mitmproxy server."""
    opts = options.Options(
        listen_host="0.0.0.0",
        listen_port=args.port,
    )

    # Configure TLS inspection
    if args.tls_inspection:
        if args.ca_pem:
            opts.certs = [args.ca_pem]
        elif args.ca_cert and args.ca_key:
            # mitmproxy needs combined PEM, create temp file
            old_umask = os.umask(0o077)
            try:
                with open(args.ca_cert, "rb") as cf, open(args.ca_key, "rb") as kf:
                    combined = kf.read() + cf.read()
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
                tmp.write(combined)
                tmp.close()
                _temp_files.append(tmp.name)
                opts.certs = [tmp.name]
            finally:
                os.umask(old_umask)

    master = DumpMaster(opts)

    if args.verbose:
        master.addons.add(VerboseLogger())

    logger.info("MITM Proxy running on port %d", args.port)
    if args.verbose:
        logger.info("Verbose logging enabled")
    if args.tls_inspection:
        logger.info("TLS inspection enabled")
    else:
        logger.info("TLS inspection disabled (tunnel mode)")
    logger.info("Press Ctrl+C to stop")

    try:
        await master.run()
    finally:
        master.shutdown()
        logger.info("Proxy stopped")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MITM Proxy for HTTP troubleshooting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Log full HTTP headers, request and response",
    )
    parser.add_argument(
        "--tls-inspection",
        action="store_true",
        help="Enable TLS inspection (default: tunnel mode)",
    )
    parser.add_argument(
        "--ca-cert",
        metavar="FILE",
        help="Path to CA certificate for TLS inspection",
    )
    parser.add_argument(
        "--ca-key",
        metavar="FILE",
        help="Path to CA private key for TLS inspection",
    )
    parser.add_argument(
        "--ca-pem",
        metavar="FILE",
        help="Path to combined CA cert+key PEM file",
    )
    parser.add_argument(
        "--generate-tls-ca",
        action="store_true",
        help="Generate CA certificate and key in current directory",
    )
    parser.add_argument(
        "--ca-cn",
        default="MITM Proxy Root CA",
        help="Common Name for generated CA (default: MITM Proxy Root CA)",
    )
    parser.add_argument(
        "--ca-org",
        default="MITM Proxy CA",
        help="Organization for generated CA (default: MITM Proxy CA)",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="Proxy port (default: 8080)",
    )

    args = parser.parse_args()

    # Validate port
    if not 1 <= args.port <= 65535:
        parser.error(f"Port must be between 1 and 65535, got {args.port}")
    if args.port < 1024:
        logger.warning("Port %d requires root/administrator privileges", args.port)

    if args.generate_tls_ca:
        generate_ca(common_name=args.ca_cn, organization=args.ca_org)
        return

    if not HAS_MITMPROXY:
        logger.error("'mitmproxy' package required")
        logger.error("Install with: pip install mitmproxy")
        sys.exit(1)

    if args.tls_inspection:
        if not args.ca_pem and not (args.ca_cert and args.ca_key):
            parser.error("--tls-inspection requires --ca-pem or both --ca-cert and --ca-key")

    # Signal handling for graceful shutdown
    def signal_handler(signum: int, frame: object) -> None:
        logger.info("Received signal %d, shutting down...", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    import asyncio
    asyncio.run(run_proxy(args))


if __name__ == "__main__":
    main()
