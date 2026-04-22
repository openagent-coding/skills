#!/usr/bin/env python3
"""
Token Counter - Estimate token count for text content.

Usage:
    python token_counter.py --text "content to analyze"
    python token_counter.py --file path/to/file.txt
    python token_counter.py --file path/to/file.txt --model claude-4-sonnet

Reads from stdin if neither --text nor --file is provided.
Output: JSON with estimated_tokens, model, context_limit, usage_percentage.
"""

import argparse
import json
import re
import sys

# Model standard context limits (tokens)
MODEL_LIMITS = {
    "claude-4-sonnet": 200_000,
    "claude-4-opus": 200_000,
    "claude-4-haiku": 200_000,
    "claude-4.5-sonnet": 200_000,
    "claude-4.5-opus": 200_000,
    "claude-4.5-haiku": 200_000,
    "claude-4.6-opus": 200_000,
}
DEFAULT_LIMIT = 200_000


def count_tokens(text: str) -> int:
    """Estimate token count from text. Returns int.

    Approximation ratios:
      - English text:     ~4   chars/token
      - Code:             ~3.5 chars/token
      - Structured data:  ~2.5 chars/token
    """
    if not text:
        return 0
    if _is_code(text):
        return max(1, int(len(text) / 3.5))
    if _is_structured_data(text):
        return max(1, int(len(text) / 2.5))
    return max(1, len(text) // 4)


def _is_code(text: str) -> bool:
    """Heuristic: does the text look like source code?"""
    indicators = [
        r'\b(function|class|def|var|let|const|import|export)\b',
        r'[{};]',
        r'^\s*(#|//)',
        r'\b(if|else|for|while|return)\b',
    ]
    return any(re.search(p, text, re.MULTILINE) for p in indicators)


def _is_structured_data(text: str) -> bool:
    """Heuristic: does the text look like JSON/XML/YAML?

    Conservative check — only triggers on text that starts with a
    structural character.  The previous implementation also matched
    any text containing both `\"` and `:`, which is far too broad.
    """
    return text.lstrip().startswith(("{", "[", "<"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate token count for text")
    parser.add_argument("--text", help="Text to analyze")
    parser.add_argument("--file", help="File to analyze")
    parser.add_argument("--model", default="claude-4-sonnet",
                        help="Claude model name (default: claude-4-sonnet)")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    tokens = count_tokens(text)
    limit = MODEL_LIMITS.get(args.model, DEFAULT_LIMIT)
    pct = round((tokens / limit) * 100, 1) if limit else 0.0

    result = {
        "estimated_tokens": tokens,
        "model": args.model,
        "context_limit": limit,
        "usage_percentage": pct,
        "exceeds_90_percent": pct >= 90.0,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
