#!/usr/bin/env python3
"""Import SuperPSX's PS4 package sources into Overdrive's catalog.

    python -P tools/import-superpsx.py crawl [--cache <dir>] [--scope catalog|all] [--limit N] [--refresh-index]
    python -P tools/import-superpsx.py import [--cache <dir>] [--scope hidden|catalog] [--write] [--report <file>]

SuperPSX (https://www.superpsx.com) is a WordPress site. Its public REST API lists the game posts
(category 46, "PS4 Games"); each post links one download page, /dll-<slug>/, laid out as

    Version ⇛ CUSA58757 – USA
    Game ⇛ MoCha – FileK – Viki – OneFile
    Update 1.03 (Fix 5.05/6.72/...) ⇛ MoCha – FileK – Viki – OneFile
    Password ⇛ SuperPSX

crawl reads the post list, then the download page of every post whose title is a PS4 game of the
catalog (--scope catalog, the default) or of every post (--scope all). The site is slow, so it waits
between pages, retries, and keeps what it read in --cache (default ../.superpsx-cache, outside the
repository): a second run reads only the pages it is missing. Nothing in the repository changes.

import reads only the cache. It keeps the links on hosts the app downloads from (VikingFile,
FileKeeper, DataNodes, AkiraBox), drops those the catalog already has (the same file on its host,
whatever the URL's spelling) and writes them as release records tagged source "superpsx" on the
catalog game with that title id, or, for another region's id, on the catalog game of the same
title. Multi-part sets are left out. Every run rebuilds the "superpsx" records from the cache and
keeps the other sources' records byte for byte. --scope hidden (the default) touches only the PS4
games the app hides today for want of a working source; --scope catalog every PS4 catalog game.
Without --write it only prints, and --report saves, what it would change.
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "app", "data")
CATALOG = os.path.join(DATA, "catalog.js")
RELEASES = os.path.join(DATA, "releases")
SITE = "https://www.superpsx.com"
API = SITE + "/wp-json/wp/v2"
PS4_GAMES = 46
SOURCE = "superpsx"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
PAUSE = 2.0

# provider, flow, label suffix (it has to start with the provider's first four letters:
# app/game/sources.js strips it back off), catalog "providers" key. As in import-pippo.py.
HOSTS = {
    "vikingfile.com": ("VikingFile", "vikingfile", "Vikingfile", "vikingfile"),
    "vik1ngfile.site": ("VikingFile", "vikingfile", "Vikingfile", "vikingfile"),
    "filekeeper.net": ("filekeeper.net", "browser", "FileKeeper", "filekeeper"),
    "datanodes.to": ("DataNodes", "datanodes", "DataNodes", "datanodes"),
    "datanodes.co": ("DataNodes", "datanodes", "DataNodes", "datanodes"),
    "akirabox.com": ("AkiraBox", "akirabox", "AkiraBox", "akirabox"),
    "akirabox.to": ("AkiraBox", "akirabox", "AkiraBox", "akirabox"),
}
# The file's own id on its host, so the same file under another spelling counts once.
FILE_IDS = (
    (("vikingfile.com", "vik1ngfile.site"), re.compile(r"^/[fd]/([A-Za-z0-9]+)")),
    (("filekeeper.net", "datanodes.to", "datanodes.co"), re.compile(r"^/([a-z0-9]{12})")),
    (("akirabox.com", "akirabox.to"), re.compile(r"^/([A-Za-z0-9]+)")),
)
# Links checked dead by hand: an import must not bring them back.
DEAD_LINKS = frozenset()
TITLE_ID = re.compile(r"\b(CUSA\d{5})\b")
REGIONS = ("USA", "EUR", "JPN", "ASIA", "HK", "KOR")
SECTION_WORD = re.compile(r"(?<![A-Za-z])(?:Game|Base|Update|All DLC|DLCs?|Fix|Backport|Patch|Version)(?![A-Za-z])", re.I)


# --- Fetching -----------------------------------------------------------------


def fetch(url, attempts=4):
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if attempt == attempts - 1:
                raise
            wait = PAUSE * 4 * (attempt + 1)
            print(f"  {url}: {error}; again in {wait:.0f} s", file=sys.stderr)
            time.sleep(wait)


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    partial = path + ".partial"
    with open(partial, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=1)
    os.replace(partial, path)


# --- The catalog ----------------------------------------------------------------

GAME_LINE = re.compile(r'^\s*\{ "id": "([^"]+)", "title": "((?:[^"\\]|\\.)*)", "platform": "(\w+)", "providers": \[([^\]]*)\]')
PROVIDERS = re.compile(r'"providers": \[[^\]]*\]')
# Hosts the app shows today (app/state/paused-hosts.js): a game whose providers are none of these is hidden.
SHOWN = {"vikingfile", "datanodes", "filekeeper", "akirabox", "archive.org", "overdrive cdn", "github"}


def title_key(title):
    title = html.unescape(title)
    title = re.sub(r"[™®©]", "", title)
    title = re.sub(r"\s+(?:PS4|PS5|PKG|PS4 PKG)\s*$", "", title, flags=re.I)
    return re.sub(r"[^a-z0-9]", "", title.lower())


def catalog_games():
    games = {}
    with open(CATALOG, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    for index, line in enumerate(lines):
        match = GAME_LINE.match(line)
        if not match or match.group(3) != "ps4":
            continue
        # A few titles carry escapes JSON does not know: they are only compared, so drop them.
        title = json.loads('"%s"' % re.sub(r"\\(?![\x22\\/bfnrtu])", "", match.group(2)))
        providers = [item.strip().strip('"') for item in match.group(4).split(",") if item.strip()]
        games[match.group(1)] = {"title": title, "providers": providers, "index": index,
                                 "hidden": not any(p.lower() in SHOWN for p in providers)}
    return games, lines


# --- Crawl ----------------------------------------------------------------------


def crawl_index(cache, refresh):
    path = os.path.join(cache, "posts.json")
    posts = read_json(path, None)
    if posts is not None and not refresh:
        return posts
    posts, page = [], 1
    while True:
        url = f"{API}/posts?categories={PS4_GAMES}&per_page=100&page={page}&_fields=id,date,modified,link,title,content"
        try:
            batch = json.loads(fetch(url))
        except urllib.error.HTTPError as error:
            if error.code == 400:  # past the last page
                break
            raise
        if not batch:
            break
        for post in batch:
            downloads = re.findall(r'href="(https://(?:www\.)?superpsx\.com/dl[^"#?]*)', post["content"]["rendered"])
            posts.append({"id": post["id"], "date": post["date"], "modified": post["modified"], "link": post["link"],
                          "title": html.unescape(post["title"]["rendered"]), "downloads": sorted(set(downloads))})
        print(f"  posts page {page}: {len(posts)} so far")
        page += 1
        time.sleep(PAUSE)
    write_json(path, posts)
    return posts


def article_of(page):
    """The part of a /dll-.../ page that holds its links."""
    start = page.find("<article")
    end = page.find("</article>", start)
    return page[start:end] if start >= 0 and end > start else page


def parse_download_page(body):
    """The sections of a download page's article: [{"version": "CUSA58757 – USA", "name": "Game", "links": [[text, url]]}]."""
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", body, flags=re.S)
    # Only the links stay as tags: every other tag ends a piece of text, so a heading reads whole.
    body = re.sub(r"<(?!/?a[\s>])[^>]*>", "\n", body)
    tokens = re.findall(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>|([^<]+)', body, flags=re.S)
    # `heading` gathers the text since the last section: the site splits a heading such as
    # "Update 1.05 (Fix 5.05/6.72+)" over several tags, and the arrow closes it.
    sections, version, name, heading = [], "", "", []
    for href, anchor, chunk in tokens:
        if href:
            if sections and name and name.lower() != "version" and re.match(r"https?://", href) and "superpsx.com" not in href:
                sections[-1]["links"].append([html.unescape(re.sub(r"<[^>]+>", "", anchor)).strip(), html.unescape(href)])
            heading = []
            continue
        for piece in html.unescape(chunk).replace("\xa0", " ").split("\n"):
            text = piece.strip()
            if not text or text in ("-", "\u2013", "|"):
                continue
            if text.endswith("\u21db"):
                joined = " ".join(heading + [text[:-1].strip()]).strip()
                heading = []
                # Credits and stray link separators can come before the heading ("Thank @x Game (9.00+)"),
                # and a page with several versions names the next one there ("CUSA07410 – EUR ... Game").
                found = TITLE_ID.search(joined)
                if found and any(region in joined for region in REGIONS):
                    version = joined[found.start():]
                # The first word that opens a section ("Update 1.07 (Fix 5.05)" is an update), past a "Version" label.
                keyword = [m for m in SECTION_WORD.finditer(joined) if m.group(0).lower() != "version"]
                name = joined[keyword[0].start():] if keyword else joined
                if name.lower() != "version":
                    sections.append({"version": version, "name": name, "links": []})
                continue
            heading.append(text)
            if name.lower() == "version" and TITLE_ID.search(text):
                version = text
                name = ""
                heading = []
    return [section for section in sections if section["links"]]


def crawl(args):
    cache = args.cache
    posts = crawl_index(cache, args.refresh_index)
    games, _ = catalog_games()
    keys = {title_key(game["title"]) for game in games.values()}
    wanted = [post for post in posts if post["downloads"] and (args.scope == "all" or title_key(post["title"]) in keys)]
    pages_dir = os.path.join(cache, "pages")
    todo = [post for post in wanted if "articles" not in read_json(os.path.join(pages_dir, f"{post['id']}.json"), {})]
    print(f"{len(posts)} posts, {len(wanted)} in scope, {len(todo)} download pages to read")
    for done, post in enumerate(todo[:args.limit] if args.limit else todo, 1):
        articles = []
        for url in post["downloads"]:
            try:
                articles.append(article_of(fetch(url)))
            except Exception as error:  # a page that keeps failing is tried again on the next run
                print(f"  {post['title']}: {error}", file=sys.stderr)
                articles = None
                break
            time.sleep(PAUSE)
        if articles is not None:
            write_json(os.path.join(pages_dir, f"{post['id']}.json"), {"post": post, "articles": articles})
        if done % 20 == 0:
            print(f"  {done}/{len(todo)}")


# --- Import ---------------------------------------------------------------------


def host_of(url):
    match = re.match(r"https?://([^/?#]+)(/[^?#]*)?", url, re.I)
    return (match.group(1).lower().removeprefix("www."), match.group(2) or "/") if match else ("", "")


def file_id(url):
    host, path = host_of(url)
    for domains, pattern in FILE_IDS:
        if any(host == d or host.endswith("." + d) for d in domains):
            found = pattern.match(path)
            if found:
                return domains[0] + ":" + found.group(1)
    return url.split("#")[0].rstrip("/")


def known_files(releases):
    seen = set()
    for records in releases.values():
        for record in records:
            if record.get("source") == SOURCE:
                continue
            for field in ("url", "browserUrl"):
                if isinstance(record.get(field), str):
                    seen.add(file_id(record[field]))
            for part in record.get("parts") or []:
                for field in ("url", "browserUrl"):
                    if isinstance(part.get(field), str):
                        seen.add(file_id(part[field]))
    return seen


def section_kind(name):
    """Base or Update, the update's version, and whether it is a multi-part set; None for the rest."""
    lower = name.lower()
    if re.search(r"\bpart\b|\bpt\.?\s*\d", lower):
        return None
    if re.match(r"^(game|base)\b", lower):
        return "Base", ""
    match = re.match(r"^update\s*v?([\d.]+)?", lower)
    if match:
        return "Update", (match.group(1) or "").strip(".")
    return None


def region_of(version, url):
    for text in (version, url):
        for region in REGIONS:
            if re.search(r"(?<![A-Z])%s(?![A-Z])" % region, text or ""):
                return region
    return ""


def record_for(title_id, url, kind, version, region, spec, extra, file_title=None):
    release_id = "r" + hashlib.sha256(("%s|%s" % (title_id, url)).encode("utf-8")).hexdigest()[:12]
    provider, flow, suffix, _ = spec
    label = " ".join(part for part in (region, kind, extra) if part) + " - " + suffix
    return {
        "id": release_id,
        "format": "pkg",
        "filename": "%s-game-%s-%s.pkg" % (title_id, version or "unknown", release_id),
        "url": url,
        "browserUrl": url,
        "requiresBrowser": True,
        "sizeBytes": None,
        "version": version,
        "category": "game",
        "provider": provider,
        "source": SOURCE,
        "flow": flow,
        "label": label,
        "platform": "ps4",
        "record": "%s-%s-%s" % (SOURCE, title_id, kind.lower()),
        # The file's own title id, when another region or edition than the game's: the queue
        # downloads by it (the browser capture looks for it), so it is not an "another game?" warning.
        **({"titleId": file_title} if file_title and file_title != title_id else {}),
    }


def read_releases():
    out = {}
    for name in sorted(os.listdir(RELEASES)):
        if name.endswith(".json"):
            with open(os.path.join(RELEASES, name), encoding="utf-8") as handle:
                out[name[:-5]] = json.load(handle)
    return out


def build_plan(args):
    games, lines = catalog_games()
    by_title = {}
    for title_id, game in games.items():
        by_title.setdefault(title_key(game["title"]), []).append(title_id)
    releases = read_releases()
    seen = known_files(releases)
    scope = {tid for tid, game in games.items() if game["hidden"]} if args.scope == "hidden" else set(games)
    # A game this import showed is no longer hidden: it stays in scope, or a second run would take
    # back the sources that showed it.
    scope |= {tid for tid, rows in releases.items() if any(r.get("source") == SOURCE for r in rows)}
    records, unmatched, skipped = {}, [], {"other host": 0, "known": 0, "part or other section": 0, "dead": 0}
    for name in sorted(os.listdir(os.path.join(args.cache, "pages"))):
        page = read_json(os.path.join(args.cache, "pages", name), None)
        if "articles" not in page:  # read by an earlier version of this tool: crawl again
            continue
        post = page["post"]
        sections = [section for article in page["articles"] for section in parse_download_page(article)]
        ids = [m for s in sections for m in TITLE_ID.findall(s["version"] + " " + " ".join(u for _, u in s["links"]))]
        same_title = by_title.get(title_key(post["title"]), [])
        target = next((tid for tid in ids if tid in games), None) or (same_title[0] if len(same_title) == 1 else None)
        if not target:
            unmatched.append(f"{post['title']} {sorted(set(ids))[:2]}")
            continue
        if target not in scope:
            continue
        for section in sections:
            kind = section_kind(section["name"])
            # Two links on one host in one section may be the parts of a set: neither is the whole file.
            per_host = {}
            for _, url in section["links"]:
                per_host[host_of(url)[0]] = per_host.get(host_of(url)[0], 0) + 1
            for text, url in section["links"]:
                if per_host[host_of(url)[0]] > 1 and any(host_of(url)[0].endswith(d) for d in HOSTS):
                    skipped["part or other section"] += 1
                    continue
                host, _ = host_of(url)
                spec = next((s for d, s in HOSTS.items() if host == d or host.endswith("." + d)), None)
                if not spec:
                    skipped["other host"] += 1
                    continue
                if not kind:
                    skipped["part or other section"] += 1
                    continue
                if url in DEAD_LINKS:
                    skipped["dead"] += 1
                    continue
                if file_id(url) in seen:
                    skipped["known"] += 1
                    continue
                seen.add(file_id(url))
                label_kind, update_version = kind
                fix = re.search(r"\(fix[^)]*\)|backport[^)]*", section["name"], re.I)
                extra = ("v" + update_version if update_version else "") + (" BackPort" if fix else "")
                file_title = (TITLE_ID.findall(url) or TITLE_ID.findall(section["version"]) or [None])[0]
                records.setdefault(target, []).append(
                    record_for(target, url, label_kind, update_version, region_of(section["version"], url), spec, extra.strip(), file_title))
    return {"games": games, "lines": lines, "releases": releases, "records": records,
            "unmatched": unmatched, "skipped": skipped}


def apply_plan(plan):
    changed = []
    titles = set(plan["records"]) | {tid for tid, rows in plan["releases"].items() if any(r.get("source") == SOURCE for r in rows)}
    for title_id in sorted(titles):
        kept = [r for r in plan["releases"].get(title_id, []) if r.get("source") != SOURCE]
        rows = kept + plan["records"].get(title_id, [])
        body = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
        path = os.path.join(RELEASES, title_id + ".json")
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != body:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(body)
            changed.append(title_id)
    lines = plan["lines"]
    for title_id, rows in plan["records"].items():
        game = plan["games"][title_id]
        keys = sorted(set(game["providers"]) | {next(s for d, s in HOSTS.items() if s[0] == r["provider"])[3] for r in rows})
        if keys != game["providers"]:
            rendered = "[" + ", ".join(json.dumps(key) for key in keys) + "]"
            lines[game["index"]] = PROVIDERS.sub('"providers": ' + rendered, lines[game["index"]], count=1)
    with open(CATALOG, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines))
    return changed


def run_import(args):
    plan = build_plan(args)
    games, records = plan["games"], plan["records"]
    revived = sorted(tid for tid in records if games[tid]["hidden"])
    already = sorted(tid for tid in records if not games[tid]["hidden"])
    by_host = {}
    for rows in records.values():
        for row in rows:
            by_host[row["provider"]] = by_host.get(row["provider"], 0) + 1
    print(f"games getting sources: {len(records)} (hidden today, shown after: {len(revived)}; already shown: {len(already)})")
    print("new links by host:", by_host)
    print("links left out:", plan["skipped"])
    print(f"posts matching no catalog game: {len(plan['unmatched'])}")
    for tid in revived[:25]:
        print(f"  shown again: {tid} {games[tid]['title']} ({len(records[tid])} links)")
    if args.report:
        write_json(args.report, {"revived": [[tid, games[tid]["title"]] for tid in revived],
                                 "records": records, "unmatched": plan["unmatched"], "skipped": plan["skipped"]})
    if args.write:
        changed = apply_plan(plan)
        print(f"wrote {len(changed)} release files and the catalog's providers")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    default_cache = os.path.join(os.path.dirname(ROOT), ".superpsx-cache")
    c = sub.add_parser("crawl")
    c.add_argument("--cache", default=default_cache)
    c.add_argument("--scope", choices=("catalog", "all"), default="catalog")
    c.add_argument("--limit", type=int, default=0, help="read at most this many download pages")
    c.add_argument("--refresh-index", action="store_true", help="read the post list again")
    i = sub.add_parser("import")
    i.add_argument("--cache", default=default_cache)
    i.add_argument("--scope", choices=("hidden", "catalog"), default="hidden")
    i.add_argument("--write", action="store_true")
    i.add_argument("--report")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    crawl(args) if args.command == "crawl" else run_import(args)


if __name__ == "__main__":
    main()
