# app/services/chunking.py
"""Cut long text into overlapping pieces that fit in a prompt and in an embedding model."""

# Where we prefer to cut, best first: a paragraph, a line, the end of a sentence, a space
BREAKS = ["\n\n", "\n", ". ", "? ", "! ", "؟ ", "، ", " "]


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Pieces of at most `size` characters. Each piece starts with the last ~`overlap` characters of the one before."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    text = text.strip()
    pieces, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            end = _best_break(text, start, end)
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        # Step back by the overlap, then forward to the start of a word, so no piece begins mid-word
        next_start = max(end - overlap, start + 1)
        if overlap:
            space = text.find(" ", next_start, end)
            if space != -1:
                next_start = space + 1
        start = next_start
    return pieces


def _best_break(text: str, start: int, end: int) -> int:
    """The best place to cut inside text[start:end], but never in its first half (no tiny pieces)."""
    earliest = start + (end - start) // 2
    for mark in BREAKS:
        position = text.rfind(mark, earliest, end)
        if position != -1:
            return position + len(mark)
    return end  # no good place: cut at the limit
