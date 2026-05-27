# extremism_matcher.py
# Advanced matching engine for extremist language detection

import re
from nltk.stem import SnowballStemmer
from rapidfuzz import fuzz
from config import (
    EXTREMISM_KEYWORDS, SYNONYM_GROUPS, PROXIMITY_PAIRS,
    PROXIMITY_WINDOW, OBFUSCATION_PATTERNS, CATEGORY_WEIGHTS
)

stemmer = SnowballStemmer('english')

def _stem(text: str) -> str:
    return ' '.join(stemmer.stem(w) for w in text.lower().split())

STEMMED_KEYWORDS = {
    category: [_stem(kw) for kw in keywords]
    for category, keywords in EXTREMISM_KEYWORDS.items()
}

STEMMED_SYNONYMS = {
    concept: [_stem(v) for v in variants]
    for concept, variants in SYNONYM_GROUPS.items()
}

CONCEPT_CATEGORY_MAP = {
    'kill':          'incitement',
    'attack':        'incitement',
    'bash_the_fash': 'incitement',
    'purge':         'ideological_extremism',
    'subhuman':      'ideological_extremism',
    'supremacist':   'ideological_extremism',
    'replacement':   'ideological_extremism',
    'racism':        'ideological_extremism',
    'fascist':       'political_extremism',
    'overthrow':     'political_extremism',
    'accelerate':    'political_extremism',
    'globalist':     'political_extremism',
    'zionist':       'hate_group_markers',
}

def normalize_text(text: str) -> str:
    for pattern, replacement in OBFUSCATION_PATTERNS:
        text = pattern.sub(f' {replacement} ', text)
    return text

def get_word_tokens(text: str) -> list[str]:
    return re.findall(r"[\w']+", normalize_text(text.lower()))

def fuzzy_match(token: str, keyword: str, threshold: int = 85) -> bool:
    if len(token) < 5 or len(keyword) < 5:
        return token == keyword
    return fuzz.ratio(token, keyword) >= threshold

def check_proximity(tokens: list[str], term_a: str, term_b: str, window: int) -> bool:
    stem_a = _stem(term_a).split()[0]
    stem_b = _stem(term_b).split()[0]
    stemmed = [stemmer.stem(t) for t in tokens]
    positions_a = [i for i, t in enumerate(stemmed) if t == stem_a]
    positions_b = [i for i, t in enumerate(stemmed) if t == stem_b]
    return any(
        abs(pa - pb) <= window
        for pa in positions_a
        for pb in positions_b
    )

def _concept_to_category(concept: str) -> str:
    return CONCEPT_CATEGORY_MAP.get(concept, 'toxicity')

def _match_keyword_list(stemmed_tok, stemmed_kws, weight, matches, raw_score):
    for kw in stemmed_kws:
        kw_tokens = kw.split()
        if kw in matches:
            continue
        if len(kw_tokens) == 1:
            for tok in stemmed_tok:
                if tok == kw_tokens[0] or fuzzy_match(tok, kw_tokens[0]):
                    matches.append(kw)
                    raw_score += weight
                    break
        else:
            for i in range(len(stemmed_tok) - len(kw_tokens) + 1):
                if stemmed_tok[i:i + len(kw_tokens)] == kw_tokens:
                    matches.append(kw)
                    raw_score += weight
                    break
    return raw_score

def _match_synonyms(stemmed_tok, matches, raw_score):
    for concept, stemmed_variants in STEMMED_SYNONYMS.items():
        cat = _concept_to_category(concept)
        tag = f'[synonym:{concept}]'
        if tag in matches[cat]:
            continue
        for variant in stemmed_variants:
            var_tokens = variant.split()
            matched = False
            if len(var_tokens) == 1:
                for tok in stemmed_tok:
                    if tok == var_tokens[0] or fuzzy_match(tok, var_tokens[0]):
                        matched = True
                        break
            else:
                for i in range(len(stemmed_tok) - len(var_tokens) + 1):
                    if stemmed_tok[i:i + len(var_tokens)] == var_tokens:
                        matched = True
                        break
            if matched:
                matches[cat].append(tag)
                raw_score += CATEGORY_WEIGHTS.get(cat, 0.5) * 0.9
                break
    return raw_score

def analyze_text(text: str) -> dict:
    if not text or not str(text).strip():
        return {
            'matches':        {cat: [] for cat in EXTREMISM_KEYWORDS},
            'proximity_hits': [],
            'raw_score':      0.0,
            'weighted_score': 0.0,
            'flags':          []
        }

    tokens      = get_word_tokens(str(text))
    stemmed_tok = [stemmer.stem(t) for t in tokens]
    matches     = {cat: [] for cat in EXTREMISM_KEYWORDS}
    raw_score   = 0.0

    for category, stemmed_kws in STEMMED_KEYWORDS.items():
        weight = CATEGORY_WEIGHTS.get(category, 0.5)
        raw_score = _match_keyword_list(
            stemmed_tok, stemmed_kws, weight, matches[category], raw_score
        )

    raw_score = _match_synonyms(stemmed_tok, matches, raw_score)

    proximity_hits = []
    for term_a, term_b, multiplier in PROXIMITY_PAIRS:
        if check_proximity(tokens, term_a, term_b, PROXIMITY_WINDOW):
            proximity_hits.append((term_a, term_b, multiplier))
            raw_score += multiplier

    weighted_score = min(round(raw_score * 10, 2), 100.0)

    flags = []
    for cat, found in matches.items():
        if found:
            flags.append(f"{cat}: {', '.join(found)}")
    for ta, tb, mult in proximity_hits:
        flags.append(f"proximity [{mult}x]: '{ta}' near '{tb}'")

    return {
        'matches':        matches,
        'proximity_hits': proximity_hits,
        'raw_score':      round(raw_score, 3),
        'weighted_score': weighted_score,
        'flags':          flags,
    }