

from __future__ import annotations
import os
import requests

GITHUB_API_URL = "https://api.github.com/search/repositories"


def get_similar_projects_with_details(query: str, max_results: int = 5) -> list[dict]:

    headers = {"Accept": "application/vnd.github+json"}

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": max_results,
    }

    try:
        response = requests.get(GITHUB_API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[github_search] request failed: {e}")
        return []

    data = response.json()
    items = data.get("items", [])
    return [
        {
            "url": item["html_url"],
            "name": item["full_name"],
            "description": item.get("description") or "",
            "stars": item["stargazers_count"],
        }
        for item in items
    ]


if __name__ == "__main__":
    #test
    urls = get_similar_projects_with_details("recipe recommendation fridge ingredients", max_results=5)
    for url in urls:
        print(url)
