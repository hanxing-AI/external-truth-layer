#!/usr/bin/env bash
# factlookup.sh — Search a local fact/knowledge base via grep.
#
# Many AI agent frameworks store persistent facts in hidden directories (e.g.
# ~/.hermes/brain/) that built-in file search tools skip by default. This
# script wraps grep to reliably find facts in any markdown knowledge base.
#
# Usage:
#   factlookup.sh <keyword>            # Search for keyword, list matches
#   factlookup.sh --index              # Print fact index (if available)
#   factlookup.sh --list               # List all files in the fact base
#
# Configuration:
#   Set FACT_DIR environment variable to your fact base directory.
# Default: ~/.local/fact-base (customize with FACT_DIR)
# Examples: ~/Documents/knowledge-base, ~/notes/facts, ~/.hermes/brain (Hermes)

FACT_DIR="${FACT_DIR:-$HOME/.local/fact-base}"
INDEX_FILE="${FACT_INDEX:-$FACT_DIR/index.md}"

if [ "$1" = "--index" ]; then
  if [ -f "$INDEX_FILE" ]; then
    cat "$INDEX_FILE"
  else
    echo "No index file found at $INDEX_FILE"
    echo "Set FACT_INDEX to point to your index file."
  fi
  exit 0
fi

if [ "$1" = "--list" ]; then
  find "$FACT_DIR" -name '*.md' -type f 2>/dev/null | sed "s|$FACT_DIR/||"
  exit 0
fi

if [ -z "$1" ]; then
  echo "Usage: factlookup.sh <keyword> | --index | --list"
  echo ""
  echo "Config:"
  echo "  FACT_DIR  — fact base directory (default: ~/.local/fact-base)"
  echo "  FACT_INDEX — index file path (default: \$FACT_DIR/index.md)"
  exit 1
fi

if [ ! -d "$FACT_DIR" ]; then
  echo "Fact directory not found: $FACT_DIR"
  echo "Set FACT_DIR to your knowledge base location."
  exit 1
fi

echo "=== Matching files ==="
grep -rl "$1" "$FACT_DIR" 2>/dev/null | sed "s|$FACT_DIR/||"
echo ""
echo "=== Matching lines (first 20) ==="
grep -rn "$1" "$FACT_DIR" 2>/dev/null | sed "s|$FACT_DIR/||" | head -20
