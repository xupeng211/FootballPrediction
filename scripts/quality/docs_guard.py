#!/usr/bin/env python3
"""
Documentation Guardian - Validates docs structure and links

Usage:
  python scripts/docs_guard.py

Checks:
1. Dead links in Markdown files
2. Orphaned documents (no incoming links)
3. Directory structure compliance
4. Required files presence
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

# Configuration
DOCS_DIR = Path("docs")
ALLOWED_TOP_DIRS = {
    "architecture",
    "how-to",
    "reference",
    "testing",
    "data",
    "ml",
    "ops",
    "release",
    "staging",
    "legacy",
    "_reports",
    "_meta",
}
REQUIRED_FILES = ["README.md", "INDEX.md"]
BANNED_PATTERNS = ["../", "~/", "C:\\", "/usr/", "/home/"]


def check_required_files():
    """Check if required documentation files exist"""
    issues = []

    for file in REQUIRED_FILES:
        filepath = DOCS_DIR / file
        if not filepath.exists():
            issues.append(f"❌ Missing required file: docs/{file}")

    return issues


def check_directory_structure():
    """Check if top-level directory structure is compliant"""
    issues = []

    if not DOCS_DIR.exists():
        return ["❌ docs/ directory does not exist"]

    for item in DOCS_DIR.iterdir():
        if item.is_dir() and item.name not in ALLOWED_TOP_DIRS:
            issues.append(f"❌ Disallowed top-level directory: docs/{item.name}/")

    return issues


def extract_links(filepath):
    """Extract all relative links from a markdown file"""
    try:
        content = filepath.read_text(encoding="utf-8")
            except Exception:
        return []

    # Find markdown links: [text](target)
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

    relative_links = []
    for text, target in links:
        # Skip absolute URLs, mailto, anchor links
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue

        # Check for banned patterns
        if any(banned in target for banned in BANNED_PATTERNS):
            continue

        relative_links.append(target)

    return relative_links


def resolve_link_path(source_file, link_target):
    """Resolve relative link to absolute path"""
    source_dir = source_file.parent
    target_path = (source_dir / link_target).resolve()

    # Try to find .md file if no extension
    if not target_path.suffix and target_path.exists():
        return target_path
    elif not target_path.suffix:
        md_path = target_path.with_suffix(".md")
        if md_path.exists():
            return md_path

    return target_path


def check_dead_links():
    """Check for dead links in documentation"""
    issues = []

    if not DOCS_DIR.exists():
        return issues

    all_files = list(DOCS_DIR.rglob("*.md"))
    {f.resolve() for f in all_files}

    for source_file in all_files:
        links = extract_links(source_file)

        for link in links:
            target_path = resolve_link_path(source_file, link)

            # Remove fragments for file existence check
            file_path = Path(str(target_path).split("#")[0])

            if not file_path.exists():
                try:
                    rel_source = source_file.relative_to(Path.cwd())
                except ValueError:
                    rel_source = str(source_file)
                issues.append(f"❌ Dead link: {rel_source} -> {link}")

    return issues


def check_orphaned_documents():
    """Check for documents that have no incoming links"""
    issues = []

    if not DOCS_DIR.exists():
        return issues

    all_files = list(DOCS_DIR.rglob("*.md"))
    file_links = defaultdict(set)

    # Build link graph
    for source_file in all_files:
        links = extract_links(source_file)
        for link in links:
            target_path = resolve_link_path(source_file, link)
            if target_path.exists() and target_path.suffix == ".md":
                file_links[target_path].add(source_file)

    # Check for orphaned files (excluding index files and legacy)
    for file in all_files:
        file_path = file.resolve()

        # Skip index files, README files, and legacy files
        if (
            file.name in ["INDEX.md", "README.md"]
            or "legacy" in str(file)
            or "_meta" in str(file)
            or "_reports" in str(file)
        ):
            continue

        # Skip files that are linked to
        if file_links[file_path]:
            continue

        # Skip files in allowed top directories that are meant to be entry points
        parent_parts = file.relative_to(DOCS_DIR).parts
        if len(parent_parts) == 1 and parent_parts[0] in ALLOWED_TOP_DIRS:
            continue

        try:
            rel_path = file.relative_to(Path.cwd())
        except ValueError:
            rel_path = str(file)
        issues.append(f"⚠️  Orphaned document: {rel_path}")

    return issues


def main():
    """Main validation function"""
    print("🛡️  Documentation Guardian")
    print("=" * 40)

    all_issues = []

    # Run all checks
    print("📋 Checking required files...")
    all_issues.extend(check_required_files())

    print("📁 Checking directory structure...")
    all_issues.extend(check_directory_structure())

    print("🔗 Checking dead links...")
    all_issues.extend(check_dead_links())

    print("👻 Checking orphaned documents...")
    all_issues.extend(check_orphaned_documents())

    # Report results
    print("\n" + "=" * 40)

    if all_issues:
        print("❌ Issues found:")
        for issue in all_issues:
            print(f"  {issue}")
        print(f"\nFound {len(all_issues)} issue(s)")
        sys.exit(1)
    else:
        print("✅ All checks passed!")
        print("Documentation is healthy and well-structured.")
        sys.exit(0)


if __name__ == "__main__":
    main()
