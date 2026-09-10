import re
from typing import Dict, List


class DocumentChunker:
    """
    Paragraph-preserving, token-bounded document chunker conforming to Blueprint §20.
    Target: ~800 tokens per chunk (500–1000 range), 100-token overlap between chunks.
    """

    def __init__(self, target_tokens: int = 800, overlap_tokens: int = 100):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        try:
            import tiktoken
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._tokenizer = None

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self._tokenizer:
            return len(self._tokenizer.encode(text, disallowed_special=()))
        # Fast fallback: whitespace word count × 1.3
        return max(1, int(len(text.split()) * 1.3))

    def split_into_paragraphs(self, text: str) -> List[str]:
        # Split on standard paragraph breaks
        raw_paras = re.split(r"\n\s*\n", text)
        cleaned = [p.strip() for p in raw_paras if p.strip()]
        if not cleaned and text.strip():
            return [text.strip()]
        return cleaned

    def chunk_document_pages(self, pages: List[Dict]) -> List[Dict]:
        """
        Takes list of dicts: [{'page_number': 1, 'text': '...'}]
        Returns list of chunk dicts:
        [{'seq': 0, 'page_from': 1, 'page_to': 2, 'text': '...', 'token_count': 780}]
        """
        # Linearize pages into paragraph units preserving page attribution
        units: List[Dict] = []
        for p in pages:
            page_num = p["page_number"]
            page_text = p.get("text") or ""
            paragraphs = self.split_into_paragraphs(page_text)
            for para in paragraphs:
                para_tokens = self.count_tokens(para)
                # If paragraph itself exceeds target, break it into sentences
                if para_tokens > self.target_tokens:
                    sentences = re.split(r"(?<=[.?!])\s+", para)
                    for sent in sentences:
                        s_text = sent.strip()
                        if s_text:
                            units.append({
                                "text": s_text,
                                "page": page_num,
                                "tokens": self.count_tokens(s_text),
                            })
                else:
                    units.append({
                        "text": para,
                        "page": page_num,
                        "tokens": para_tokens,
                    })

        if not units:
            return []

        chunks: List[Dict] = []
        current_unit_indices: List[int] = []
        current_tokens = 0
        seq = 0
        i = 0

        while i < len(units):
            unit = units[i]
            current_unit_indices.append(i)
            current_tokens += unit["tokens"]

            if current_tokens >= self.target_tokens or i == len(units) - 1:
                chunk_text = "\n\n".join(units[idx]["text"] for idx in current_unit_indices)
                pages_in_chunk = [units[idx]["page"] for idx in current_unit_indices]
                chunks.append({
                    "seq": seq,
                    "page_from": min(pages_in_chunk),
                    "page_to": max(pages_in_chunk),
                    "text": chunk_text,
                    "token_count": current_tokens,
                })
                seq += 1

                if i == len(units) - 1:
                    break

                # Overlap calculation: step back until overlap threshold is met
                overlap_accum = 0
                step_back_idx = i
                while step_back_idx >= 0 and overlap_accum < self.overlap_tokens:
                    overlap_accum += units[step_back_idx]["tokens"]
                    step_back_idx -= 1

                next_start_idx = max(step_back_idx + 1, current_unit_indices[0] + 1)
                i = next_start_idx
                current_unit_indices = []
                current_tokens = 0
            else:
                i += 1

        return chunks