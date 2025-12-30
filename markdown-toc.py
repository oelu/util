#!/usr/bin/env python3
"""
Generate and insert a table of contents into markdown files.

Usage:
    markdown-toc.py <file.md>              # Modify file in-place
    markdown-toc.py <file.md> --stdout     # Print to stdout
    markdown-toc.py <file.md> -o out.md    # Write to different file
"""

import argparse
import re
import sys
from typing import List, Tuple


def heading_to_anchor(text: str) -> str:
    """Convert heading text to GitHub-style anchor.

    Args:
        text: Heading text to convert

    Returns:
        Anchor string (lowercase, hyphens, no special chars)
    """
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text)
    # Strip inline code markers but keep content
    text = re.sub(r'`([^`]+)`', r'\1', text)
    anchor = text.lower()
    anchor = re.sub(r'[^\w\s-]', '', anchor)
    anchor = re.sub(r'\s+', '-', anchor)
    anchor = re.sub(r'-+', '-', anchor)
    return anchor.strip('-')


def extract_headings(lines: List[str]) -> List[Tuple[int, str, int]]:
    """Extract headings from markdown lines, skipping code blocks.

    Args:
        lines: List of markdown lines

    Returns:
        List of (level, text, line_index) tuples
    """
    headings = []
    in_code_block = False
    code_fence = None

    for idx, line in enumerate(lines):
        stripped = line.strip()

        # Check for code fence start/end
        if stripped.startswith('```') or stripped.startswith('~~~'):
            fence = stripped[:3]
            if not in_code_block:
                in_code_block = True
                code_fence = fence
            elif stripped.startswith(code_fence):
                in_code_block = False
                code_fence = None
            continue

        if in_code_block:
            continue

        # Skip indented code blocks (4+ spaces or tab)
        if line.startswith('    ') or line.startswith('\t'):
            continue

        # Match heading (must not be indented)
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append((level, text, idx))

    return headings


def generate_toc(headings: List[Tuple[int, str, int]],
                 max_level: int = 3,
                 skip_first: bool = True) -> str:
    """Generate TOC markdown from headings list.

    Args:
        headings: List of (level, text, line_index) tuples
        max_level: Maximum heading depth to include (1-6)
        skip_first: If True, skip first heading (typically document title)

    Returns:
        Formatted TOC as markdown string, or empty string if no headings
    """
    if not headings:
        return ''

    toc_headings = headings[1:] if skip_first and headings else headings
    if not toc_headings:
        return ''

    # Find minimum level for proper indentation
    min_level = min(h[0] for h in toc_headings)

    lines = []
    anchor_counts = {}  # Track anchor usage for deduplication
    for level, text, _ in toc_headings:
        if level > max_level:
            continue
        indent = '  ' * (level - min_level)
        anchor = heading_to_anchor(text)

        # Handle duplicate anchors GitHub-style
        if anchor in anchor_counts:
            anchor_counts[anchor] += 1
            anchor = f'{anchor}-{anchor_counts[anchor]}'
        else:
            anchor_counts[anchor] = 0

        lines.append(f'{indent}- [{text}](#{anchor})')

    return '\n'.join(lines)


def insert_toc(content: str, toc: str) -> str:
    """Insert TOC after first heading, replacing existing TOC if present.

    Args:
        content: Full markdown file content
        toc: Generated TOC string to insert

    Returns:
        Modified content with TOC inserted
    """
    lines = content.split('\n')

    # Remove existing TOC block
    toc_start = None
    toc_end = None
    for i, line in enumerate(lines):
        if line.strip() == '<!-- TOC -->':
            toc_start = i
        elif line.strip() == '<!-- /TOC -->' and toc_start is not None:
            toc_end = i
            break

    if toc_start is not None and toc_end is not None:
        lines = lines[:toc_start] + lines[toc_end + 1:]

    # Find first heading (proper fence tracking)
    first_heading_idx = None
    in_code_block = False
    code_fence = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('```') or stripped.startswith('~~~'):
            fence = stripped[:3]
            if not in_code_block:
                in_code_block = True
                code_fence = fence
            elif stripped.startswith(code_fence):
                in_code_block = False
                code_fence = None
            continue
        if in_code_block:
            continue
        if re.match(r'^#{1,6}\s+', line):
            first_heading_idx = i
            break

    if first_heading_idx is None:
        # No heading found, prepend TOC
        toc_block = f'<!-- TOC -->\n{toc}\n<!-- /TOC -->\n\n'
        return toc_block + content

    # Insert TOC after first heading
    toc_block = ['', '<!-- TOC -->', toc, '<!-- /TOC -->']
    result = lines[:first_heading_idx + 1] + toc_block + lines[first_heading_idx + 1:]

    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(
        description='Generate and insert a table of contents into markdown files.'
    )
    parser.add_argument('file', help='Markdown file to process')
    parser.add_argument('-o', '--output', help='Write to FILE instead of modifying in-place')
    parser.add_argument('-l', '--levels', type=int, default=3,
                        help='Max heading depth to include (1-6, default: 3)')
    parser.add_argument('--stdout', action='store_true',
                        help='Print result to stdout instead of modifying file')
    parser.add_argument('--include-first', action='store_true',
                        help='Include first heading in TOC')

    args = parser.parse_args()

    if not 1 <= args.levels <= 6:
        print('Error: --levels must be between 1 and 6', file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f'Error: File not found: {args.file}', file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f'Error reading file: {e}', file=sys.stderr)
        sys.exit(1)

    lines = content.split('\n')
    headings = extract_headings(lines)
    toc = generate_toc(headings, max_level=args.levels, skip_first=not args.include_first)

    if not toc:
        print('No headings found to generate TOC', file=sys.stderr)
        sys.exit(0)

    result = insert_toc(content, toc)

    if args.stdout:
        print(result)
    else:
        output_path = args.output or args.file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            if not args.output:
                print(f'TOC added to {args.file}')
            else:
                print(f'TOC written to {output_path}')
        except IOError as e:
            print(f'Error writing file: {e}', file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
