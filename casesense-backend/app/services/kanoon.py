# pyrefly: ignore [missing-import]
import httpx
import re
import html
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class KanoonService:
    def __init__(self):
        self.api_key = settings.INDIANKANOON_API_KEY
        self.base_url = settings.LEGAL_SOURCE_BASE_URL.rstrip('/')

    def _strip_html(self, html_content: str) -> str:
        """Removes HTML tags to save tokens for the LLM."""
        if not html_content:
            return ""
        text = re.sub(r'<[^>]+>', ' ', html_content)
        # Collapse multiple spaces/newlines into single space
        text = re.sub(r'\s+', ' ', html.unescape(text))
        return text.strip()

    def _normalise_doc(self, raw: dict, doc_id: str = "") -> dict:
        """Map Indian Kanoon's actual field names to a consistent schema.

        The API uses non-obvious keys:
          tid       -> docid
          docsource -> court
          publishdate -> decided_on
          author / bench -> judges
        """
        docid = str(raw.get("tid") or raw.get("docid") or doc_id)
        title = raw.get("title", "Unknown Case")
        court = raw.get("docsource") or raw.get("court") or "Unknown Court"
        decided_on = raw.get("publishdate", "")
        
        # Extract judges from author or bench
        judges = []
        if raw.get("author"):
            judges.append(raw["author"])
        elif raw.get("bench"):
            judges = [str(j) for j in raw["bench"]] if isinstance(raw["bench"], list) else [str(raw["bench"])]

        # Strip HTML from the doc body if present
        text = ""
        if "doc" in raw:
            text = self._strip_html(raw["doc"])
        elif "text" in raw:
            text = raw["text"]

        return {
            "docid": docid,
            "title": title,
            "court": court,
            "decided_on": decided_on,
            "judges": judges,
            "text": text,
            "url": f"https://indiankanoon.org/doc/{docid}/",
            "citation": raw.get("citation", ""),
            # These are actual authority links supplied by Indian Kanoon, not
            # AI-generated snippets. ``citeList`` is what this judgment cites;
            # ``citedbyList`` is later authority citing this judgment.
            "cited_authorities": self._normalise_citation_list(
                raw.get("citeList") or raw.get("cites") or []
            ),
            "cited_by": self._normalise_citation_list(
                raw.get("citedbyList") or raw.get("citedby") or []
            ),
        }

    def _normalise_citation_list(self, items: Any) -> List[Dict[str, str]]:
        if not isinstance(items, list):
            return []
        authorities: List[Dict[str, str]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            docid = str(item.get("tid") or item.get("docid") or item.get("id") or "")
            title = str(item.get("title") or item.get("doc_title") or "")
            citation = str(item.get("citation") or item.get("cite") or "")
            if title or citation or docid:
                authorities.append({
                    "docid": docid,
                    "title": title or "Indian Kanoon authority",
                    "citation": citation,
                    "court": str(item.get("docsource") or item.get("court") or ""),
                    "url": f"https://indiankanoon.org/doc/{docid}/" if docid else "",
                })
        return authorities

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Searches Indian Kanoon for cases matching the query."""
        if not self.api_key:
            logger.warning("No Kanoon API key provided. Cannot search.")
            return []

        url = f"{self.base_url}/search/"
        headers = {"Authorization": f"Token {self.api_key}"}
        data = {"formInput": query, "pagenum": 0}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data)
                response.raise_for_status()
            result = response.json()
            raw_docs = result.get("docs", [])
            # Normalise field names immediately so downstream code never
            # needs to guess between tid/docid/docsource/court etc.
            return [self._normalise_doc(d) for d in raw_docs]
        except Exception as e:
            logger.exception("Failed to search IndianKanoon.", error=str(e))
            return []

    async def get_judgment(self, docid: str) -> Optional[Dict[str, Any]]:
        """Fetches the full judgment text from Indian Kanoon."""
        if not self.api_key:
            logger.warning("No Kanoon API key. Cannot fetch judgment.")
            return None

        url = f"{self.base_url}/doc/{docid}/"
        headers = {"Authorization": f"Token {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    params={"maxcites": 25, "maxcitedby": 25},
                )
                response.raise_for_status()
                raw = response.json()
                return self._normalise_doc(raw, doc_id=docid)
        except Exception as e:
            logger.exception(f"Failed to get judgment {docid}.", error=str(e))
            return None
