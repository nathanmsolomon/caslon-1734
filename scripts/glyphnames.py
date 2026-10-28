"""Shared glyph naming: source label -> (production glyph name, unicode or None)."""

NAMES = {
    "&": ("ampersand", 0x26), ",": ("comma", 0x2C), "-": ("hyphen", 0x2D),
    ".": ("period", 0x2E), ":": ("colon", 0x3A), ";": ("semicolon", 0x3B),
    "?": ("question", 0x3F), "!": ("exclam", 0x21), "'": ("quotesingle", 0x27),
    "(": ("parenleft", 0x28), ")": ("parenright", 0x29),
    "Æ": ("AE", 0xC6), "æ": ("ae", 0xE6), "Œ": ("OE", 0x152), "œ": ("oe", 0x153), "ê": ("ecircumflex", 0xEA),
    "ſ": ("longs", 0x17F), "ë": ("edieresis", 0xEB), "î": ("icircumflex", 0xEE),
    # Caslon cast only old-style (hanging) figures; they go on the plain digits
    "0": ("zero", 0x30), "1": ("one", 0x31), "2": ("two", 0x32), "3": ("three", 0x33),
    "4": ("four", 0x34), "5": ("five", 0x35), "6": ("six", 0x36), "7": ("seven", 0x37),
    "8": ("eight", 0x38), "9": ("nine", 0x39),
    "ff": ("f_f", 0xFB00), "fi": ("f_i", 0xFB01), "fl": ("f_l", 0xFB02),
    "ffi": ("f_f_i", 0xFB03), "ffl": ("f_f_l", 0xFB04), "ct": ("c_t", None),
    "ſi": ("longs_i", None), "ſt": ("longs_t", 0xFB05), "ſſi": ("longs_longs_i", None),
    "ſſ": ("longs_longs", None), "ſh": ("longs_h", None), "ſk": ("longs_k", None), "ſl": ("longs_l", None), "ſb": ("longs_b", None),
}

# sequences (in source characters) that a layout engine replaces with a ligature,
# longest first; used by our own proof renderer
LIGATURES = ["ſſi", "ffi", "ffl", "ſſ", "ſi", "ſt", "ſh", "ſk", "ſl", "ſb", "ff", "fi", "fl"]


def glyph_name(ch):
    if ch in NAMES:
        return NAMES[ch]
    if ch.endswith(".sc"):          # small capitals: a.sc, b.sc ... (no Unicode)
        return ch[0].lower() + ".sc", None
    return ch, ord(ch)
