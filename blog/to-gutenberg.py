#!/usr/bin/env python3
"""blog/post.html（プレーン HTML）から blog/post-gutenberg.html（ブロックマークアップ）を生成する。

post.html を編集したら、このスクリプトを実行して両方を同期させること。
    python3 blog/to-gutenberg.py
"""
import re
import sys
from pathlib import Path

SRC = Path(__file__).parent / "post.html"
DST = Path(__file__).parent / "post-gutenberg.html"

# 開始タグ -> 終了タグ（複数行にまたがりうる要素）
MULTILINE = {
    "<pre": "</pre>",
    "<ul": "</ul>",
    "<ol": "</ol>",
    "<figure": "</figure>",
    "<blockquote": "</blockquote>",
    "<div": "</div>",
}


def split_elements(text):
    """トップレベル要素を 1 つずつ切り出す。"""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        opener = next((o for o in MULTILINE if line.startswith(o)), None)
        if opener:
            closer = MULTILINE[opener]
            buf = [line]
            while closer not in "\n".join(buf):
                i += 1
                if i >= len(lines):
                    sys.exit(f"閉じタグ {closer} が見つかりません")
                buf.append(lines[i])
            yield "\n".join(buf)
        else:
            yield line
        i += 1


def wrap_list(el):
    """<ul>/<ol> の各 <li> を wp:list-item で包む。"""
    ordered = el.startswith("<ol")
    open_tag = "<!-- wp:list {\"ordered\":true} -->" if ordered else "<!-- wp:list -->"
    items = re.findall(r"<li>.*?</li>", el, re.S)
    inner = "".join(
        f"<!-- wp:list-item -->\n{it}\n<!-- /wp:list-item -->" for it in items
    )
    tag = "ol" if ordered else "ul"
    return f"{open_tag}\n<{tag}>{inner}</{tag}>\n<!-- /wp:list -->"


def to_block(el):
    if el.startswith("<pre"):
        return f"<!-- wp:code -->\n{el}\n<!-- /wp:code -->"
    if el.startswith("<div"):
        # 画像挿入位置の指示ブロックなど、生 HTML をそのまま置く
        return f"<!-- wp:html -->\n{el}\n<!-- /wp:html -->"
    if el.startswith(("<p>", "<p ")):
        return f"<!-- wp:paragraph -->\n{el}\n<!-- /wp:paragraph -->"
    if el.startswith("<h2"):
        return f"<!-- wp:heading -->\n{el}\n<!-- /wp:heading -->"
    if el.startswith("<h3"):
        return f'<!-- wp:heading {{"level":3}} -->\n{el}\n<!-- /wp:heading -->'
    if el.startswith("<hr"):
        return f"<!-- wp:separator -->\n{el}\n<!-- /wp:separator -->"
    if el.startswith(("<ul", "<ol")):
        return wrap_list(el)
    if el.startswith("<blockquote"):
        body = re.sub(r"^<blockquote[^>]*>|</blockquote>$", "", el)
        inner = f"<!-- wp:paragraph -->\n{body}\n<!-- /wp:paragraph -->"
        return (
            "<!-- wp:quote -->\n"
            f'<blockquote class="wp-block-quote">{inner}</blockquote>\n'
            "<!-- /wp:quote -->"
        )
    if el.startswith("<figure"):
        if "wp-block-table" in el:
            return f"<!-- wp:table -->\n{el}\n<!-- /wp:table -->"
        if "wp-block-image" in el:
            return (
                '<!-- wp:image {"align":"center","sizeSlug":"large"} -->\n'
                f"{el}\n<!-- /wp:image -->"
            )
    sys.exit(f"未対応の要素です: {el[:60]}")


def main():
    blocks = [to_block(el) for el in split_elements(SRC.read_text(encoding="utf-8"))]
    DST.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"{DST.name}: {len(blocks)} ブロック生成")


if __name__ == "__main__":
    main()
