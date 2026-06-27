"""Pure text-parsing utilities for extracting media from LLM responses.

No I/O -- just regex-based extraction of media blocks from text.
Lives in domain/shared so both API and infrastructure layers can import it.

Ported from PropertyBot with property-specific constructs (PropertyAlbum,
PROPERTY_ALBUM blocks, inject_property_images) removed. Sight keeps
the general media extraction infrastructure for images, videos, and
documents that the LLM may embed in responses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Fallback: markdown image syntax ![alt](url) -- character classes are bounded
# so there is no catastrophic-backtracking risk.
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


# Media block markers -- handled via str.find() instead of regex to eliminate any
# possibility of catastrophic backtracking on adversarial LLM output.
_MEDIA_KINDS = ("IMAGES", "VIDEOS", "DOCUMENTS")


def _find_blocks(text: str, kind: str) -> list[tuple[int, int, str]]:
    """Return [(start, end, inner_content)] for every <<<KIND>>>...<<</KIND>>> block.

    Linear-time scan with ``str.find``. Tolerates trailing-``>`` truncation on
    the closing tag (LLM sometimes writes ``>>`` instead of ``>>>``).
    """
    open_tag = f"<<<{kind}>>>"
    close_variants = (f"<<</{kind}>>>", f"<<</{kind}>>")
    blocks: list[tuple[int, int, str]] = []
    cursor = 0
    while True:
        start = text.find(open_tag, cursor)
        if start < 0:
            return blocks
        content_start = start + len(open_tag)
        end = -1
        end_tag_len = 0
        for cv in close_variants:
            candidate = text.find(cv, content_start)
            if candidate >= 0 and (end < 0 or candidate < end):
                end = candidate
                end_tag_len = len(cv)
        if end < 0:
            return blocks
        blocks.append((start, end + end_tag_len, text[content_start:end]))
        cursor = end + end_tag_len


@dataclass
class MediaGroup:
    """A group of media items with optional caption."""

    urls: list[str] = field(default_factory=list)
    caption: str = ""


@dataclass
class ExtractedMedia:
    """Media URLs extracted from LLM response, grouped by type."""

    images: list[MediaGroup] = field(default_factory=list)
    videos: list[MediaGroup] = field(default_factory=list)
    documents: list[MediaGroup] = field(default_factory=list)

    def has_any(self) -> bool:
        return bool(self.images or self.videos or self.documents)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict for DB storage."""

        def _group(g: MediaGroup) -> dict[str, Any]:
            d: dict[str, Any] = {"urls": g.urls}
            if g.caption:
                d["caption"] = g.caption
            return d

        return {
            "images": [_group(g) for g in self.images],
            "videos": [_group(g) for g in self.videos],
            "documents": [_group(g) for g in self.documents],
        }


def _parse_media_block(content: str) -> MediaGroup:
    """Parse a media block: optional caption (first non-URL line) + URLs."""
    lines = [ln.strip() for ln in content.strip().splitlines() if ln.strip()]
    if not lines:
        return MediaGroup()

    caption = ""
    urls: list[str] = []

    for i, line in enumerate(lines):
        if line.startswith("http"):
            urls = [ln for ln in lines[i:] if ln.startswith("http")]
            break
        caption = line if not caption else f"{caption} {line}"

    return MediaGroup(urls=urls, caption=caption)


def _extract_fallback_images(text: str) -> tuple[str, list[str]]:
    """Fallback: extract ![alt](url) markdown images from text."""
    urls: list[str] = []
    for match in _MD_IMAGE_RE.finditer(text):
        url = match.group(1).strip()
        if url and url not in urls:
            urls.append(url)
    cleaned = _MD_IMAGE_RE.sub("", text) if urls else text
    return cleaned, urls


def extract_media(text: str) -> tuple[str, ExtractedMedia]:
    """Extract media URLs from response text.

    Primary: parses IMAGES, VIDEOS, DOCUMENTS blocks.
    Fallback: extracts ![alt](url) markdown images if no blocks found.

    Returns (cleaned_text, ExtractedMedia).
    """
    media = ExtractedMedia()
    block_map: dict[str, list[MediaGroup]] = {
        "IMAGES": media.images,
        "VIDEOS": media.videos,
        "DOCUMENTS": media.documents,
    }

    # Extract standard media blocks (with optional caption)
    media_spans: list[tuple[int, int]] = []
    for kind in _MEDIA_KINDS:
        for start, end, content in _find_blocks(text, kind):
            group = _parse_media_block(content)
            if group.urls:
                block_map[kind].append(group)
            media_spans.append((start, end))
    cleaned = _strip_spans(text, media_spans)

    # Fallback: if nothing found, try markdown image syntax
    if not media.has_any():
        cleaned, fallback_urls = _extract_fallback_images(cleaned)
        if fallback_urls:
            media.images.append(MediaGroup(urls=fallback_urls))

    # Clean up leftover blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip(), media


def _strip_spans(text: str, spans: list[tuple[int, int]]) -> str:
    """Remove the given character ranges from ``text`` and stitch the rest back."""
    if not spans:
        return text
    spans_sorted = sorted(spans, key=lambda s: s[0])
    parts: list[str] = []
    cursor = 0
    for start, end in spans_sorted:
        if start < cursor:
            # Overlapping span -- skip (shouldn't happen with non-overlapping finds)
            continue
        parts.append(text[cursor:start])
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)
