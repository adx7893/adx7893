import os
import re
import json
import datetime
import urllib.request
import xml.etree.ElementTree as ET

USER = os.environ.get("GH_USER", "adx7893")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
FEED = os.environ.get("BLOG_FEED", "").strip()
EXCLUDE = re.compile(os.environ.get("EXCLUDE", r"^(lab|talkr)"), re.I)
START = "<!-- ACTIVITY:START -->"
END = "<!-- ACTIVITY:END -->"


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def recent_repos(limit=5):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "profile-updater"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    url = f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed"
    data = json.loads(get(url, h))
    keep = [
        r for r in data
        if not r["fork"]
        and not r["archived"]
        and r["name"].lower() != USER.lower()
        and not EXCLUDE.search(r["name"])
    ]
    keep.sort(key=lambda r: r["pushed_at"], reverse=True)
    return keep[:limit]


def blog_posts(limit=5):
    if not FEED:
        return []
    root = ET.fromstring(get(FEED, {"User-Agent": "profile-updater"}))
    posts = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            posts.append((title, link))
    return posts[:limit]


def build():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%b %d, %Y")
    out = ["### Recently updated projects", ""]
    for r in recent_repos():
        bits = [x for x in [r.get("description"), r.get("language")] if x]
        tail = f": {' | '.join(bits)}" if bits else ""
        out.append(f"* [{r['name']}]({r['html_url']}){tail}")
    posts = blog_posts()
    if posts:
        out += ["", "### Latest writing", ""]
        out += [f"* [{t}]({u})" for t, u in posts]
    out += ["", f"<sub>Auto updated on {now}</sub>"]
    return "\n".join(out)


def main():
    text = open("README.md", encoding="utf-8").read()
    if START not in text or END not in text:
        raise SystemExit("README markers not found")
    block = f"{START}\n{build()}\n{END}"
    new = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        lambda m: block,
        text,
        flags=re.S,
    )
    open("README.md", "w", encoding="utf-8").write(new)


if __name__ == "__main__":
    main()
