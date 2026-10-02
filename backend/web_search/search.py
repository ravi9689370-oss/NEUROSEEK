"""
NeuroSeek AI — Web Search Service
Multiple free APIs: DuckDuckGo, Wikipedia, NewsAPI
"""

import re
import json
from typing import Optional
from urllib.request import urlopen, Request
from urllib.parse import quote_plus
from urllib.error import URLError


class WebSearch:
    """Web search service using multiple free APIs"""

    def __init__(self):
        self.base_url = "https://api.duckduckgo.com/"
        self.wikipedia_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
        self.user_agent = "NeuroSeekAI/1.0"

    def search(self, query: str, max_results: int = 5) -> list:
        """Search web using multiple sources"""
        results = []

        # 1. DuckDuckGo Instant Answer API
        try:
            url = f"{self.base_url}?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
            req = Request(url, headers={"User-Agent": self.user_agent})
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", query),
                    "snippet": data["AbstractText"],
                    "url": data.get("AbstractURL", ""),
                    "source": "DuckDuckGo"
                })

            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:100],
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo"
                    })
        except (URLError, Exception):
            pass

        # 2. Wikipedia API
        try:
            wiki_query = query.split()[0] if query.split() else query
            url = f"{self.wikipedia_url}{quote_plus(wiki_query)}"
            req = Request(url, headers={"User-Agent": self.user_agent})
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            if data.get("extract"):
                results.append({
                    "title": data.get("title", query),
                    "snippet": data["extract"],
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "source": "Wikipedia"
                })
        except (URLError, Exception):
            pass

        return results[:max_results]

    def is_available(self) -> bool:
        """Check if web search is available"""
        try:
            url = f"{self.base_url}?q=test&format=json&no_html=1"
            req = Request(url, headers={"User-Agent": self.user_agent})
            with urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False
