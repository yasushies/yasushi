"""Pixabayから投稿に使う写真を1枚探してダウンロードする。

使い方:
    PIXABAY_API_KEY=... python3 pixabay_photo.py "towel spa" out.jpg [--orientation vertical] [--exclude 123,456]

標準出力に「写真ID<TAB>ページURL<TAB>撮影者」を1行で出す。
同じ写真を何度も使わないように、使ったIDは --exclude で渡す。
"""
import argparse
import json
import os
import random
import sys
import urllib.parse
import urllib.request

API = "https://pixabay.com/api/"
# Pixabay は Python 既定の User-Agent を 403 で弾くので、通常のブラウザ名を名乗る
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; cocowa-instagram/1.0)"}


def get(url, timeout):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout)


def search(key, query, orientation):
    params = {
        "key": key,
        "q": query[:100],
        "image_type": "photo",
        "orientation": orientation,
        "safesearch": "true",
        "min_width": 1080,
        "per_page": 30,
        "order": "popular",
    }
    with get(f"{API}?{urllib.parse.urlencode(params)}", 30) as r:
        return json.load(r).get("hits", [])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("out")
    p.add_argument("--orientation", default="all", choices=["all", "horizontal", "vertical"])
    p.add_argument("--exclude", default="")
    a = p.parse_args()

    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        sys.exit("PIXABAY_API_KEY が設定されていません")

    used = {s for s in a.exclude.split(",") if s.strip()}
    hits = [h for h in search(key, a.query, a.orientation) if str(h["id"]) not in used]
    if not hits:
        sys.exit(f"写真が見つかりません: {a.query}")

    # 人気上位から少しばらつかせて選ぶ
    hit = random.choice(hits[:10])
    with get(hit["largeImageURL"], 60) as r, open(a.out, "wb") as f:
        f.write(r.read())
    print(f'{hit["id"]}\t{hit["pageURL"]}\t{hit.get("user", "")}')


if __name__ == "__main__":
    main()
