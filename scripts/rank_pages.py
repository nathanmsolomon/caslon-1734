"""Rank a book's pages by how many wanted characters its OCR text contains.

Usage: python -I rank_pages.py <djvu.xml> <wanted_chars> [n_pages]

Prints 'index count' for the best pages (index = IA page number n, 0-based,
the order of OBJECT elements in the djvu.xml).
"""
import sys, re, html

xml, wanted = sys.argv[1], set(sys.argv[2])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
pages = open(xml, encoding="utf-8", errors="replace").read().split("<OBJECT")[1:]
scores = []
for i, p in enumerate(pages):
    words = [html.unescape(w) for w in re.findall(r"<WORD[^>]*>([^<]*)</WORD>", p)]
    scores.append((sum(ch in wanted for w in words for ch in w), len(words), i))
for s, nw, i in sorted(scores, reverse=True)[:n]:
    print(i, s, nw)
