"""Tools shared by agents. Currently: web search (DuckDuckGo, Wikipedia as fallback). No API key needed."""
import requests

Hit = dict  # {"title": str, "url": str, "snippet": str}


def web_search(query: str, n: int = 4) -> list[Hit]:
    try:
        from ddgs import DDGS

        hits = [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in DDGS().text(query, max_results=n)
        ]
        if hits:
            return hits
    except Exception:  # noqa: BLE001  (rate limits, network) -> fall back
        pass
    return _wikipedia(query, n)


def _wikipedia(query: str, n: int) -> list[Hit]:
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query, "srlimit": n, "format": "json"},
            headers={"User-Agent": "eval-agent-system/0.1"},
            timeout=15,
        )
        r.raise_for_status()
        return [
            {
                "title": h["title"],
                "url": "https://en.wikipedia.org/wiki/" + h["title"].replace(" ", "_"),
                "snippet": h["snippet"].replace('<span class="searchmatch">', "").replace("</span>", ""),
            }
            for h in r.json()["query"]["search"]
        ]
    except Exception:  # noqa: BLE001
        return []


def format_hits(hits: list[Hit]) -> str:
    if not hits:
        return "(no search results)"
    return "\n".join(f"[{i}] {h['title']} ({h['url']}): {h['snippet']}" for i, h in enumerate(hits))
