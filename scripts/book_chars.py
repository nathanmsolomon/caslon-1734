"""Print the characters of a size that came only from book sources (not the sheet).

Usage: python -I book_chars.py <glyphs.json> <candidate_chars>

A glyph is book-only when every impression in its average came from a book
page directory (named n<digits>). Prints those of <candidate_chars> that are,
so the plausibility check never judges (and never removes) a sheet letter.
"""
import sys, json, re

g = json.load(open(sys.argv[1], encoding="utf-8"))["glyphs"]
book = {v["ch"] for v in g.values() if v.get("copies") and all(re.fullmatch(r"n\d+", c) for c in v["copies"])}
print("".join(c for c in sys.argv[2] if c in book))
