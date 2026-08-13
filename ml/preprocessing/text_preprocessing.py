"""Text normalization shared by training and inference.

Using the exact same transform at train time and serve time avoids
train/serve skew — both `ml.categorization.train` and
`ml.categorization.predict` import this function rather than each
implementing their own cleanup.
"""

import re

_REF_NUMBER_RE = re.compile(r"\b\d{4,}\b")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")
_MULTI_SPACE_RE = re.compile(r"\s+")

# Structural/protocol tokens common in bank & UPI narrations that carry no
# category signal on their own (e.g. "UPI/SWIGGY/123456" -> "upi" is noise,
# "swiggy" is signal).
NOISE_TOKENS = {"upi", "pos", "neft", "imps", "ref", "txn", "wdl", "no"}


def normalize_description(text: str) -> str:
    """Lowercase, strip long numeric reference codes and punctuation, and
    drop known noise tokens. Returns a cleaned string ready for TF-IDF.
    """
    text = text.lower()
    text = _REF_NUMBER_RE.sub(" ", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    tokens = [t for t in text.split() if t not in NOISE_TOKENS]
    text = " ".join(tokens)
    return _MULTI_SPACE_RE.sub(" ", text).strip()
