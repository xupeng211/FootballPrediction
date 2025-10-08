#!/usr/bin/env python3
"""
Process orphaned documents automatically based on content analysis.
"""

import re
import shutil
from pathlib import Path
from datetime import datetime

DOCS_DIR = Path("docs")
INDEX_FILE = DOCS_DIR / "INDEX.md"
LEGACY_DIR = DOCS_DIR / "legacy"


def analyze_document_value(filepath):
    """Analyze document to determine if it should be kept or archived"""
    try:
        content = filepath.read_text(encoding="utf-8")

        # Keywords that indicate valuable content
        valuable_keywords = [
            "architecture",
            "design",
            "implementation",
            "setup",
            "installation",
            "configuration",
            "tutorial",
            "guide",
            "overview",
            "reference",
            "strategy",
            "planning",
            "development",
            "deployment",
            "testing",
            "monitoring",
            "security",
            "performance",
            "optimization",
            "best practices",
            "standards",
            "specification",
            "requirements",
        ]

        # Keywords that indicate outdated content
        outdated_keywords = [
            "deprecated",
            "obsolete",
            "legacy",
            "old",
            "previous version",
            "outdated",
            "no longer supported",
            "replaced by",
            "migration",
            "completion report",
            "phase completion",
            "final report",
            "summary",
        ]

        # Check file age (files older than 6 months tend to be outdated)
        file_age = datetime.fromtimestamp(filepath.stat().st_mtime)
        days_old = (datetime.now() - file_age).days

        # Count valuable and outdated keywords
        valuable_score = sum(
            1 for keyword in valuable_keywords if keyword.lower() in content.lower()
        )
        outdated_score = sum(
            1 for keyword in outdated_keywords if keyword.lower() in content.lower()
        )

        # Additional heuristics
        is_large_file = (
            filepath.stat().st_size > 5000
        )  # Large files are often more comprehensive
        has_code_blocks = len(re.findall(r"```", content)) >= 2
        has_links = len(re.findall(r"\[.*\]\(.*\)", content)) >= 3

        # Decision logic
        if valuable_score > outdated_score and (
            is_large_file or has_code_blocks or has_links
        ):
            return "keep", valuable_score, outdated_score
        elif outdated_score > valuable_score or days_old > 180:
            return "archive", valuable_score, outdated_score
        else:
            # Edge case: small, recent files with mixed signals - keep for review
            return "review", valuable_score, outdated_score

    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return "archive", 0, 0  # Default to archive if unreadable


def add_to_index(filepath, category="Uncategorized"):
    """Add document to INDEX.md"""
    try:
        rel_path = filepath.relative_to(DOCS_DIR)

        # Read title from file
        content = filepath.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = (
            title_match.group(1)
            if title_match
            else rel_path.stem.replace("_", " ").title()
        )

        # Add to INDEX.md
        with open(INDEX_FILE, "a", encoding="utf-8") as f:
            f.write(f"- [{title}]({rel_path}) - {category}\n")

        print(f"✅ Added to INDEX.md: {rel_path}")
        return True

    except Exception as e:
        print(f"Error adding {filepath} to index: {e}")
        return False


def archive_document(filepath):
    """Move document to legacy directory"""
    try:
        LEGACY_DIR.mkdir(exist_ok=True)
        rel_path = filepath.relative_to(DOCS_DIR)
        legacy_path = LEGACY_DIR / rel_path.name

        # Ensure parent directory exists
        legacy_path.parent.mkdir(exist_ok=True)

        # Move file
        shutil.move(str(filepath), str(legacy_path))
        print(f"📦 Archived to legacy: {rel_path} -> legacy/{rel_path.name}")
        return True

    except Exception as e:
        print(f"Error archiving {filepath}: {e}")
        return False


def process_orphan(orphan_path):
    """Process a single orphan document"""
    print(f"\n🔍 Processing: {orphan_path}")

    if not orphan_path.exists():
        print(f"❌ File not found: {orphan_path}")
        return False

    decision, valuable_score, outdated_score = analyze_document_value(orphan_path)

    print(f"   Analysis: valuable={valuable_score}, outdated={outdated_score}")

    if decision == "keep":
        # Determine category based on filename
        filename = orphan_path.name.lower()
        if "security" in filename:
            category = "Security"
        elif "coverage" in filename or "testing" in filename:
            category = "Testing"
        elif "ci" in filename or "deployment" in filename:
            category = "CI/CD"
        elif "api" in filename:
            category = "API"
        elif "database" in filename or "data" in filename:
            category = "Data"
        elif "performance" in filename or "optimization" in filename:
            category = "Performance"
        else:
            category = "General"

        success = add_to_index(orphan_path, category)
        if success:
            print(f"✅ Kept and indexed: {orphan_path.relative_to(DOCS_DIR)}")

    elif decision == "archive":
        success = archive_document(orphan_path)
        if success:
            print(f"📦 Archived: {orphan_path.relative_to(DOCS_DIR)}")

    elif decision == "review":
        # For review cases, default to keeping but note for manual review
        success = add_to_index(orphan_path, "Needs Review")
        if success:
            print(f"⚠️  Kept for manual review: {orphan_path.relative_to(DOCS_DIR)}")

    return True


def main():
    """Main processing function"""
    import sys

    print("🔧 Orphan Document Processor")
    print("=" * 40)

    # Read orphan list from file argument or default
    if len(sys.argv) > 1:
        orphan_file = Path(sys.argv[1])
    else:
        orphan_file = Path("docs/_meta/orphans_batch1.txt")

    if not orphan_file.exists():
        print(f"❌ Orphan list file not found: {orphan_file}")
        return

    with open(orphan_file, "r") as f:
        orphan_paths = [line.strip() for line in f if line.strip()]

    print(f"📋 Processing {len(orphan_paths)} orphan documents...")

    processed = 0
    for orphan_path_str in orphan_paths:
        orphan_path = Path(orphan_path_str)
        if process_orphan(orphan_path):
            processed += 1

    print(
        f"\n📊 Processing complete: {processed}/{len(orphan_paths)} documents processed"
    )


if __name__ == "__main__":
    main()
