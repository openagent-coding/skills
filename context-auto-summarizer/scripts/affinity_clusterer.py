#!/usr/bin/env python3
"""
Affinity Clusterer - Group conversation segments by semantic similarity.

Usage:
    python affinity_clusterer.py --input conversation.txt --threshold 0.8
    python affinity_clusterer.py --input conversation.txt --output clusters.json

Output: JSON with segments, clusters, affinity scores, and code change maps.
"""

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

# ---- Stop words for Jaccard similarity ----
STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "it", "its", "this", "that", "and",
    "or", "but", "not", "if", "then", "i", "you", "he", "she", "we",
    "they", "me", "my", "your", "as", "so", "no", "yes", "up", "out",
})

# ---- Data classes ----

@dataclass
class Segment:
    """A single segment of conversation context."""
    id: str
    content: str
    segment_type: str          # user_message | assistant_response | tool_use | tool_result
    start_pos: int
    end_pos: int
    token_count: int
    embedding: Optional[List[float]] = None


@dataclass
class Cluster:
    """A group of related segments."""
    id: str
    segments: List[Segment]
    cluster_type: str          # code_changes | research | discussion | tool_operations | general
    affinity_score: float
    priority_score: float
    total_tokens: int = 0

# ---- Parsing ----

_SEGMENT_PATTERNS = [
    (re.compile(r'Human:.*?(?=\nAssistant:|\n<function_calls>|\Z)', re.DOTALL), "user_message"),
    (re.compile(r'Assistant:.*?(?=\nHuman:|\n<function_calls>|\Z)', re.DOTALL),  "assistant_response"),
    (re.compile(r'<function_calls>.*?</function_calls>', re.DOTALL),              "tool_use"),
    (re.compile(r'<function_results>.*?</function_results>', re.DOTALL),           "tool_result"),
]


def _intervals_overlap(start: int, end: int, intervals: List[tuple]) -> bool:
    """Check whether [start, end) overlaps any existing interval."""
    for istart, iend in intervals:
        if start < iend and end > istart:
            return True
    return False


def _parse_jsonl(text: str) -> Optional[List[Segment]]:
    """Try to parse text as JSONL conversation format (Claude Code native).

    Returns None if the text is not valid JSONL.
    """
    lines = text.strip().splitlines()
    if not lines:
        return None

    messages = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            return None  # Not JSONL
        if isinstance(obj, dict) and "role" in obj:
            messages.append(obj)
        elif isinstance(obj, dict) and "type" in obj:
            messages.append(obj)

    if not messages:
        return None

    role_map = {
        "user": "user_message",
        "human": "user_message",
        "assistant": "assistant_response",
        "tool": "tool_result",
        "tool_use": "tool_use",
        "function": "tool_result",
    }

    segments = []
    pos = 0
    for idx, msg in enumerate(messages):
        role = msg.get("role", msg.get("type", "unknown"))
        seg_type = role_map.get(role, "assistant_response")

        # Extract content from various formats
        content = ""
        raw_content = msg.get("content", "")
        if isinstance(raw_content, str):
            content = raw_content
        elif isinstance(raw_content, list):
            parts = []
            for block in raw_content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    if block.get("type") == "tool_use":
                        seg_type = "tool_use"
                        parts.append(json.dumps(block, indent=2))
                    elif block.get("type") == "tool_result":
                        seg_type = "tool_result"
                        parts.append(str(block.get("content", block.get("output", ""))))
                    else:
                        parts.append(block.get("text", str(block)))
            content = "\n".join(parts)

        content = content.strip()
        if not content:
            continue

        end_pos = pos + len(content)
        seg = Segment(
            id=f"seg_{len(segments):04d}",
            content=content,
            segment_type=seg_type,
            start_pos=pos,
            end_pos=end_pos,
            token_count=max(1, len(content) // 4),
        )
        seg.embedding = _embedding(content)
        segments.append(seg)
        pos = end_pos + 1

    return segments if segments else None


def _parse_plain_text(text: str) -> List[Segment]:
    """Parse plain-text conversation (Human:/Assistant: markers or freeform)."""
    raw_matches: List[tuple] = []  # (start, end, content, type)
    used_intervals: List[tuple] = []

    for pattern, seg_type in _SEGMENT_PATTERNS:
        for m in pattern.finditer(text):
            start, end = m.span()
            if _intervals_overlap(start, end, used_intervals):
                continue
            content = m.group(0).strip()
            if content:
                raw_matches.append((start, end, content, seg_type))
                used_intervals.append((start, end))

    # Sort by position
    raw_matches.sort(key=lambda t: t[0])

    # If no structured matches found, treat the whole text as segments
    # split by blank-line-separated blocks
    if not raw_matches:
        raw_matches = _split_freeform(text)

    segments = []
    for idx, (start, end, content, seg_type) in enumerate(raw_matches):
        seg = Segment(
            id=f"seg_{idx:04d}",
            content=content,
            segment_type=seg_type,
            start_pos=start,
            end_pos=end,
            token_count=max(1, len(content) // 4),
        )
        seg.embedding = _embedding(content)
        segments.append(seg)

    return segments


def _split_freeform(text: str) -> List[tuple]:
    """Split unstructured text into segments by blank lines or --- separators."""
    blocks = re.split(r'\n\s*\n|\n---+\n', text)
    matches = []
    pos = 0
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        start = text.find(block, pos)
        if start == -1:
            start = pos
        end = start + len(block)
        # Guess type from content
        lower = block.lower()
        if any(kw in lower for kw in ("function_calls", "tool_use", "<invoke")):
            seg_type = "tool_use"
        elif any(kw in lower for kw in ("function_results", "tool_result", "<output")):
            seg_type = "tool_result"
        else:
            seg_type = "assistant_response"
        matches.append((start, end, block, seg_type))
        pos = end
    return matches


def parse_conversation(text: str) -> List[Segment]:
    """Parse conversation text into ordered Segment objects.

    Supports JSONL (Claude Code native format) and plain text with
    Human:/Assistant: markers or freeform paragraphs.
    """
    # Try JSONL first
    segments = _parse_jsonl(text)
    if segments:
        return segments

    # Fall back to plain text parsing
    return _parse_plain_text(text)

# ---- Embeddings (lightweight feature vector) ----

_TECH_TERMS = [
    "function", "class", "method", "variable", "import", "export",
    "api", "endpoint", "request", "response", "database", "query",
    "component", "service", "config", "test", "debug", "error",
]


def _embedding(text: str) -> List[float]:
    """Build a simple feature vector for semantic comparison."""
    lower = text.lower()

    vec: List[float] = []
    # Technical-term counts
    for term in _TECH_TERMS:
        vec.append(float(lower.count(term)))
    # Structural flags
    vec.append(1.0 if "```" in text or "<code>" in text else 0.0)
    vec.append(1.0 if re.search(r'[\w\-._/]+\.[\w]{2,4}', text) else 0.0)
    vec.append(1.0 if text.lstrip().startswith(("{", "[")) else 0.0)
    vec.append(1.0 if "http" in lower else 0.0)
    vec.append(float(min(5, len(text) // 200)))

    # Normalise
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec

# ---- Similarity helpers ----

def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _jaccard(text1: str, text2: str) -> float:
    """Word-level Jaccard similarity with stop-word filtering."""
    w1 = set(re.findall(r'\b\w+\b', text1.lower())) - STOP_WORDS
    w2 = set(re.findall(r'\b\w+\b', text2.lower())) - STOP_WORDS
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def _type_similarity(t1: str, t2: str) -> float:
    if t1 == t2:
        return 1.0
    groups = [
        {"user_message", "assistant_response"},
        {"tool_use", "tool_result"},
    ]
    for g in groups:
        if t1 in g and t2 in g:
            return 0.7
    return 0.1

# ---- Clustering ----

class AffinityClusterer:
    """Group segments by semantic affinity."""

    def __init__(self, threshold: float = 0.8, min_size: int = 2):
        self.threshold = threshold
        self.min_size = min_size
        self._cache: Dict[tuple, float] = {}

    def _affinity(self, a: Segment, b: Segment) -> float:
        """Pairwise affinity with caching (avoids O(n^3) recomputation)."""
        key = (a.id, b.id) if a.id < b.id else (b.id, a.id)
        if key not in self._cache:
            emb = _cosine(a.embedding, b.embedding) if a.embedding and b.embedding else 0.0
            jac = _jaccard(a.content, b.content)
            typ = _type_similarity(a.segment_type, b.segment_type)
            prox = 1.0 / (1.0 + abs(a.start_pos - b.start_pos) / 10_000)
            self._cache[key] = emb * 0.4 + jac * 0.3 + typ * 0.2 + prox * 0.1
        return self._cache[key]

    def cluster(self, segments: List[Segment]) -> List[Cluster]:
        if not segments:
            return []

        self._cache.clear()
        clusters: List[Cluster] = []
        remaining = set(range(len(segments)))
        tried_seeds: set = set()
        cluster_id = 0

        while remaining:
            # Pick highest-priority untried segment as seed
            seed_idx = self._pick_seed(segments, remaining, tried_seeds)
            if seed_idx is None:
                break
            tried_seeds.add(seed_idx)
            remaining.discard(seed_idx)

            members = [seed_idx]
            for idx in list(remaining):
                if self._affinity(segments[seed_idx], segments[idx]) >= self.threshold:
                    members.append(idx)

            if len(members) >= self.min_size:
                # Commit cluster
                for idx in members:
                    remaining.discard(idx)
                segs = [segments[i] for i in members]
                clusters.append(Cluster(
                    id=f"cluster_{cluster_id:04d}",
                    segments=segs,
                    cluster_type=_cluster_type(segs),
                    affinity_score=self._avg_affinity(segs),
                    priority_score=_priority(segs),
                    total_tokens=sum(s.token_count for s in segs),
                ))
                cluster_id += 1
            else:
                # Seed failed — put it back but mark as tried
                remaining.add(seed_idx)

        # Remaining singletons: keep user messages and high-priority tool ops
        for idx in remaining:
            seg = segments[idx]
            if seg.segment_type == "user_message" or _seg_priority(seg) > 0.7:
                clusters.append(Cluster(
                    id=f"cluster_{cluster_id:04d}",
                    segments=[seg],
                    cluster_type=_segment_category(seg),
                    affinity_score=1.0,
                    priority_score=_seg_priority(seg),
                    total_tokens=seg.token_count,
                ))
                cluster_id += 1

        return clusters

    def _pick_seed(self, segments, remaining, tried):
        candidates = remaining - tried
        if not candidates:
            return None
        return max(candidates, key=lambda i: _seg_priority(segments[i]))

    def _avg_affinity(self, segs: List[Segment]) -> float:
        if len(segs) <= 1:
            return 1.0
        total = 0.0
        n = 0
        for i, a in enumerate(segs):
            for b in segs[i + 1:]:
                total += self._affinity(a, b)
                n += 1
        return total / n if n else 0.0

# ---- Segment classification ----

def _segment_category(seg: Segment) -> str:
    """Classify a single segment by its content."""
    content = seg.content.lower()

    # Code operations detected purely by content keywords
    if re.search(r'\b(edit|write|read|file_path|function|class)\b', content):
        return "code_changes"

    # Research
    if re.search(r'\b(search|documentation|reference)\b', content) or "websearch" in content:
        return "research"

    # Conversation
    if seg.segment_type in ("user_message", "assistant_response"):
        if re.search(r'\b(how|what|why|explain|understand|help)\b', content):
            return "discussion"
        return "general"

    # Tool operations (tool_use / tool_result without code keywords)
    if seg.segment_type in ("tool_use", "tool_result"):
        return "tool_operations"

    return "general"


def _cluster_type(segs: List[Segment]) -> str:
    counts: Dict[str, int] = {}
    for s in segs:
        t = _segment_category(s)
        counts[t] = counts.get(t, 0) + 1
    return max(counts, key=counts.get) if counts else "general"

# ---- Priority scoring ----

def _seg_priority(seg: Segment) -> float:
    score = 0.5
    if seg.segment_type == "user_message":
        score += 0.2
    if seg.segment_type in ("tool_use", "tool_result"):
        score += 0.3
    lower = seg.content.lower()
    if any(kw in lower for kw in ("function", "class", "api", "database", "config", "error", "debug")):
        score += 0.1
    score += min(0.3, len(seg.content) / 5000)
    return min(1.0, score)


def _priority(segs: List[Segment]) -> float:
    if not segs:
        return 0.0
    weights = [1.0 + i * 0.1 for i in range(len(segs))]
    scores = [_seg_priority(s) for s in segs]
    return sum(s * w for s, w in zip(scores, weights)) / sum(weights)

# ---- Code-change extraction (for affinity chart) ----

def _extract_code_changes(segs: List[Segment]) -> List[Dict]:
    changes = []
    for seg in segs:
        if seg.segment_type not in ("tool_use", "tool_result"):
            continue
        if "Edit" not in seg.content and "Write" not in seg.content:
            continue
        m = re.search(r'"file_path":\s*"([^"]+)"', seg.content)
        if not m:
            continue
        path = m.group(1)
        if '"old_string":' in seg.content and '"new_string":' in seg.content:
            ctype = "edit"
        elif '"content":' in seg.content and "Write" in seg.content:
            ctype = "create"
        else:
            ctype = "unknown"
        changes.append({"file_path": path, "change_type": ctype})
    return changes

# ---- Output formatting ----

def _build_output(segments: List[Segment], clusters: List[Cluster]) -> Dict:
    """Build the JSON output with affinity chart and code-change map."""
    cluster_list = []
    code_map: Dict[str, list] = {}
    type_counts: Dict[str, int] = {}
    aff_dist = {"high": 0, "medium": 0, "low": 0}

    for cl in clusters:
        ct = cl.cluster_type
        type_counts[ct] = type_counts.get(ct, 0) + 1
        if cl.affinity_score >= 0.8:
            aff_dist["high"] += 1
        elif cl.affinity_score >= 0.6:
            aff_dist["medium"] += 1
        else:
            aff_dist["low"] += 1

        changes = _extract_code_changes(cl.segments)
        cluster_list.append({
            "id": cl.id,
            "type": cl.cluster_type,
            "affinity_score": round(cl.affinity_score, 4),
            "priority_score": round(cl.priority_score, 4),
            "token_count": cl.total_tokens,
            "segment_count": len(cl.segments),
            "segment_ids": [s.id for s in cl.segments],
            "code_changes": changes,
        })
        for ch in changes:
            code_map.setdefault(ch["file_path"], []).append({
                "cluster_id": cl.id,
                "change_type": ch["change_type"],
                "affinity_score": round(cl.affinity_score, 4),
            })

    return {
        "summary": {
            "total_segments": len(segments),
            "total_clusters": len(clusters),
            "cluster_types": type_counts,
            "affinity_distribution": aff_dist,
            "total_tokens": sum(cl.total_tokens for cl in clusters),
        },
        "clusters": cluster_list,
        "code_changes_map": code_map,
    }

# ---- CLI ----

def main() -> None:
    parser = argparse.ArgumentParser(description="Cluster conversation segments by affinity")
    parser.add_argument("--input", required=True, help="Conversation text file (use '-' for stdin)")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")
    parser.add_argument("--threshold", type=float, default=0.8, help="Affinity threshold (default: 0.8)")
    parser.add_argument("--min-size", type=int, default=2, help="Minimum cluster size (default: 2)")
    args = parser.parse_args()

    if args.input == "-":
        text = sys.stdin.read()
    else:
        with open(args.input, "r") as f:
            text = f.read()

    segments = parse_conversation(text)
    clusterer = AffinityClusterer(args.threshold, args.min_size)
    clusters = clusterer.cluster(segments)
    result = _build_output(segments, clusters)

    output = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(output)

    # Summary to stderr
    s = result["summary"]
    print(f"Segments: {s['total_segments']}  Clusters: {s['total_clusters']}  "
          f"Tokens: {s['total_tokens']:,}", file=sys.stderr)


if __name__ == "__main__":
    main()
