# config.py
# Configuration settings for the Social Media Analytics Tool

import re

# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

DB_CONFIG = {
    'host':               '127.0.0.1',
    'user':               'root',
    'password':           'root',
    'database':           'social_analytics',
    'auth_plugin':        'mysql_native_password',
    'port':               3308,
    'use_pure':           True
}

# ---------------------------------------------------------------------------
# EXTREMISM KEYWORDS
# Organized as: universal | right-coded | left-coded
# Keywords require context-aware scoring — many appear in legitimate discourse.
# ---------------------------------------------------------------------------

EXTREMISM_KEYWORDS = {

    'incitement': [
        # Universal — explicit calls to violence, highest weight
        'kill', 'attack', 'assault', 'destroy', 'annihilate',
        'decapitate', 'lynch', 'hang', 'burn', 'bomb',
        'shoot', 'stab', 'mutilate', 'massacre', 'execute',
        'eradicate', 'wipe out', 'smash', 'violence',

        # Right-coded incitement
        'race war', 'racial war', 'day of the rope',
        'armed march on', 'bring weapons',

        # Left-coded incitement
        'bash the fash', 'kill fascists', 'kill all fascists',
        'punch a nazi', 'guillotine the elites',
        'string up the wealthy', 'by any means necessary',
        'no platform by force',
    ],

    'ideological_extremism': [
        # Universal dehumanization
        'subhuman', 'inferior', 'undesirable', 'infestation',
        'plague', 'vermin', 'parasite', 'purge', 'cleansing',
        'genocide', 'ethnic cleansing', 'exterminate',
        'racism', 'systemic racism',

        # Right-coded
        'white supremacist', 'race traitor', 'demographic replacement',
        'great replacement', 'white genocide', 'ethnostate',
        'racial purity', 'blood and soil', '1488', 'accelerationism',
        'master race', 'aryan nation',

        # Left-coded
        'class traitor', 'kulak', 'liquidate the opposition',
        'bourgeois enemy', 'reactionary must die',
        'revolutionary tribunal', 'decolonize by force',
        'die cis scum', 'whiteness is a disease',
    ],

    'political_extremism': [
        # Universal
        'overthrow', 'armed revolt', 'armed conflict', 'civil war',
        'insurrection', 'revolutionary violence', 'seize power',
        'fascist', 'fascism',   # context-dependent; flagged for review

        # Right-coded
        'deep state', 'government conspiracy', 'globalist agenda',
        'elite cabal', 'new world order', 'shadow government',
        'ZOG', 'communist takeover', 'totalitarian takeover',

        # Left-coded
        'smash the state', 'burn it all down',
        'accelerate the collapse', 'guillotine the elites',
        'fascist takeover',     # used across spectrum
    ],

    'misinformation': [
        # Universal
        'fake news', 'hoax', 'conspiracy', 'cover-up', 'exposed',
        'they dont want you to know', 'leaked', 'wake up sheeple',
        'do your own research', 'mainstream media lies',
        'red pill', 'illuminati', 'planted evidence',
        'false flag operation',

        # Right-coded
        'election was stolen', 'voter fraud proof',
        'crisis actor', 'deep state plot',

        # Left-coded
        'capitalism causes all disease', 'police invented crime',
        'whiteness is a disease', 'all prisons are concentration camps',
    ],

    'hate_group_markers': [
        # Context-dependent — low weight alone, high when paired (see PROXIMITY_PAIRS)
        'zionist',              # legitimate in geopolitical debate; flagged when
                                # paired with dehumanizing or conspiratorial language

        # Right-coded
        '1488', 'heil', 'white power', 'aryan nation',
        'proud boys', 'accelerate the collapse',

        # Left-coded
        'red army faction', 'antifa violence',
        'bash the fash', 'by any means necessary',
    ]
}

# ---------------------------------------------------------------------------
# SYNONYM / CONCEPT GROUPS
# Maps canonical concepts to linguistic variants and alternate phrasings.
# The matcher expands these automatically — add variants here only.
# ---------------------------------------------------------------------------

SYNONYM_GROUPS = {
    # Violence
    'kill':         ['kill', 'killed', 'killing', 'murder', 'murdered',
                     'assassinate', 'execute', 'execution', 'terminate',
                     'eliminated', 'exterminate', 'liquidate'],
    'attack':       ['attack', 'attacked', 'assault', 'assaulted',
                     'strike', 'strike back', 'take action', 'action needed'],
    'bash_the_fash':['bash the fash', 'punch a nazi', 'punch nazis',
                     'hit fascists', 'beat fascists', 'kill fascists',
                     'kill all fascists'],
    'purge':        ['purge', 'purged', 'purging', 'cleanse', 'cleansed',
                     'remove', 'removal', 'get rid of', 'wipe out'],

    # Dehumanization
    'subhuman':     ['subhuman', 'inhuman', 'animal', 'beasts', 'vermin',
                     'insects', 'parasites', 'disease', 'infestation', 'plague'],
    'supremacist':  ['supremacist', 'supremacy', 'superior race',
                     'master race', 'chosen people'],

    # Ideological
    'fascist':      ['fascist', 'fascism', 'nazi', 'nazism',
                     'authoritarian extremist', 'brownshirt'],
    'overthrow':    ['overthrow', 'overthrowing', 'topple', 'toppling',
                     'take down', 'bring down', 'seize power', 'tear it down'],
    'accelerate':   ['accelerate', 'accelerationism', 'speed up collapse',
                     'hasten the fall', 'let it burn', 'burn it down'],
    'globalist':    ['globalist', 'globalism', 'global elite',
                     'one world government', 'world government',
                     'new world order', 'shadow government', 'deep state'],
    'replacement':  ['replacement', 'great replacement', 'white replacement',
                     'demographic replacement', 'white genocide',
                     'invaded', 'invasion of our culture'],
    'racism':       ['racism', 'racist', 'racial hatred', 'race hate',
                     'white supremacy', 'systemic racism'],
    'zionist':      ['zionist', 'zionism', 'zionist conspiracy',
                     'zionist control', 'ZOG'],
}

# ---------------------------------------------------------------------------
# PROXIMITY PAIRS
# Dangerous term combinations scored higher than either term alone.
# Format: (term_a, term_b, score_multiplier)
# Fires when term_a appears within PROXIMITY_WINDOW words of term_b.
# ---------------------------------------------------------------------------

PROXIMITY_WINDOW = 10   # words to scan left and right

PROXIMITY_PAIRS = [
    # Explicit incitement
    ('kill',        'police',       1.5),
    ('kill',        'government',   1.5),
    ('kill',        'liberal',      1.5),
    ('kill',        'conservative', 1.5),   # balanced
    ('kill',        'fascist',      2.0),
    ('kill',        'all',          1.8),
    ('murder',      'politician',   2.0),
    ('assassinate', 'leader',       2.5),
    ('attack',      'police',       1.4),
    ('attack',      'synagogue',    2.5),
    ('attack',      'mosque',       2.5),
    ('attack',      'church',       2.5),
    ('burn',        'down',         1.5),
    ('armed',       'revolution',   2.0),
    ('armed',       'march',        1.8),
    ('bring',       'weapons',      2.0),
    ('civil war',   'soon',         1.8),

    # Dehumanization combinations
    ('subhuman',    'immigrant',    2.0),
    ('subhuman',    'jewish',       2.5),
    ('vermin',      'replace',      2.0),
    ('purge',       'traitor',      2.0),
    ('eliminate',   'enemy',        1.8),

    # Conspiracy + action
    ('deep state',  'must be stopped', 1.8),
    ('globalist',   'control',      1.5),
    ('zionist',     'control',      1.8),
    ('zionist',     'conspiracy',   2.0),
    ('accelerate',  'collapse',     1.7),
    ('overthrow',   'government',   2.0),
    ('violence',    'government',   1.4),

    # Left-coded incitement combinations
    ('guillotine',  'billionaire',  1.8),
    ('guillotine',  'politician',   2.0),
    ('string up',   'landlord',     1.8),
    ('bash',        'fash',         2.0),
    ('punch',       'fascist',      1.8),
    ('smash',       'state',        1.5),
    ('by any means','necessary',    1.5),
]

# ---------------------------------------------------------------------------
# OBFUSCATION PATTERNS
# Regex patterns catching letter substitution and spacing tricks.
# Compiled once at load time for performance.
# ---------------------------------------------------------------------------

OBFUSCATION_PATTERNS = [
    # Letter substitutions
    (re.compile(r'k[\W_]*[i1!|][\W_]*l[\W_]*l',    re.IGNORECASE), 'kill'),
    (re.compile(r'd[\W_]*[i1!|][\W_]*[e3]',         re.IGNORECASE), 'die'),
    (re.compile(r'h[\W_]*[a@4][\W_]*t[\W_]*[e3]',   re.IGNORECASE), 'hate'),
    (re.compile(r'm[\W_]*[a@4][\W_]*s[\W_]*s[\W_]*[a@4][\W_]*c[\W_]*r[\W_]*[e3]',
                                                     re.IGNORECASE), 'massacre'),
    (re.compile(r'a[\W_]*s[\W_]*s[\W_]*[a@4][\W_]*s[\W_]*s[\W_]*[i1!][\W_]*n',
                                                     re.IGNORECASE), 'assassin'),
    (re.compile(r'n[\W_]*[i1!|][\W_]*g[\W_]*g',     re.IGNORECASE), 'slur_racial'),
    (re.compile(r'f[\W_]*[a@4][\W_]*g',             re.IGNORECASE), 'slur_homophobic'),

    # Spaced-out letters: "k i l l", "k.i.l.l"
    (re.compile(r'\bk\s*[.\-_]?\s*i\s*[.\-_]?\s*l\s*[.\-_]?\s*l\b',
                                                     re.IGNORECASE), 'kill'),
    (re.compile(r'\bh\s*[.\-_]?\s*a\s*[.\-_]?\s*t\s*[.\-_]?\s*e\b',
                                                     re.IGNORECASE), 'hate'),
]

# ---------------------------------------------------------------------------
# RISK SCORING
# ---------------------------------------------------------------------------

# How much each keyword category contributes to the raw extremism score
CATEGORY_WEIGHTS = {
    'incitement':            1.0,
    'hate_group_markers':    0.85,
    'ideological_extremism': 0.90,
    'political_extremism':   0.70,
    'misinformation':        0.50,
}

# Risk level thresholds for UI flagging
RISK_THRESHOLDS = {
    'ai_profile_high':      70,
    'ai_profile_medium':    40,
    'fake_profile_high':    70,
    'fake_profile_medium':  40,
    'toxicity_high':        70,
    'toxicity_medium':      40,
    'extremism_high':       60,
    'extremism_medium':     30,
}

# ---------------------------------------------------------------------------
# TOXICITY KEYWORDS
# Standalone list for the toxicity-specific scoring pipeline
# ---------------------------------------------------------------------------

TOXICITY_KEYWORDS = [
    'hate', 'kill', 'die', 'stupid', 'idiot', 'dumb', 'loser',
    'trash', 'garbage', 'worthless', 'pathetic', 'disgusting',
    'scum', 'filth', 'vile', 'despicable', 'abominable',
    'you deserve to die', 'should be shot',
    'die cis scum', 'all cops deserve death',
    'string up the wealthy',
]

# ---------------------------------------------------------------------------
# FILE UPLOAD SETTINGS
# ---------------------------------------------------------------------------

MAX_FILE_SIZE   = 10 * 1024 * 1024     # 10 MB
ALLOWED_FORMATS = ['csv', 'json', 'xlsx']