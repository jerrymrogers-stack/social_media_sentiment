# analyzer.py
# Scoring and risk analysis for the Social Media Analytics Tool

from textblob import TextBlob
from config import TOXICITY_KEYWORDS, RISK_THRESHOLDS, EXTREMISM_KEYWORDS
from extremism_matcher import analyze_text


class Analyzer:

    # ---------------------------------------------------------------------------
    # TEXT-LEVEL SCORING
    # ---------------------------------------------------------------------------

    @staticmethod
    def _safe_text(text) -> str:
        """Normalize input to a clean string. Returns empty string if invalid."""
        return str(text).strip() if text and str(text).strip() else ''

    @staticmethod
    def calculate_sentiment(text) -> float:
        """
        Sentiment polarity via TextBlob.
        Returns float in range [-1.0, 1.0].
        Negative = negative sentiment, positive = positive sentiment.
        """
        t = Analyzer._safe_text(text)
        if not t:
            return 0.0
        try:
            return float(TextBlob(t).sentiment.polarity)
        except Exception as e:
            print(f"✗ Sentiment error: {e}")
            return 0.0

    @staticmethod
    def calculate_extremism_score(text) -> float:
        """
        Extremism score (0–100) via the advanced extremism_matcher.
        Includes keyword matching, synonym expansion, proximity pairs,
        and obfuscation detection.
        """
        t = Analyzer._safe_text(text)
        if not t:
            return 0.0
        try:
            result = analyze_text(t)
            return result['weighted_score']
        except Exception as e:
            print(f"✗ Extremism analysis error: {e}")
            return 0.0

    @staticmethod
    def calculate_toxicity_score(text) -> float:
        """
        Toxicity score (0–100) based on TOXICITY_KEYWORDS from config.
        Score = percentage of toxicity keywords present in the text.
        """
        t = Analyzer._safe_text(text)
        if not t:
            return 0.0

        t_lower = t.lower()
        matches = sum(1 for kw in TOXICITY_KEYWORDS if kw.lower() in t_lower)
        return min(100.0, (matches / len(TOXICITY_KEYWORDS)) * 100) if TOXICITY_KEYWORDS else 0.0

    @staticmethod
    def calculate_misinformation_score(text) -> float:
        """
        Misinformation score (0–100) using the misinformation keyword list
        from EXTREMISM_KEYWORDS in config — single source of truth,
        no duplicated keyword list.
        """
        t = Analyzer._safe_text(text)
        if not t:
            return 0.0

        keywords = EXTREMISM_KEYWORDS.get('misinformation', [])
        if not keywords:
            return 0.0

        t_lower = t.lower()
        matches = sum(1 for kw in keywords if kw.lower() in t_lower)
        return min(100.0, (matches / len(keywords)) * 100)

    @staticmethod
    def analyze_post(post_text) -> dict:
        """
        Analyze a single post and return all text-level scores.
        This is the primary per-post entry point.
        """
        return {
            'sentiment_score':      Analyzer.calculate_sentiment(post_text),
            'extremism_score':      Analyzer.calculate_extremism_score(post_text),
            'toxicity_score':       Analyzer.calculate_toxicity_score(post_text),
            'misinformation_score': Analyzer.calculate_misinformation_score(post_text),
        }

    # ---------------------------------------------------------------------------
    # PROFILE-LEVEL RISK SCORING
    # ---------------------------------------------------------------------------

    @staticmethod
    def calculate_ai_profile_risk(posts_df, profile_data) -> float:
        """
        AI/Bot profile risk (0–100).

        Factors and weights:
          25% — Linguistic consistency  (low variance in post length = bot-like)
          20% — Posting interval consistency (regular timing = bot-like)
          20% — Content diversity (low unique word ratio = bot-like)
          20% — Engagement consistency (uniform likes/comments = bot-like)
          15% — Account metrics (age and follower ratio)
        """
        if posts_df is None or len(posts_df) == 0:
            return 0.0

        risk_scores = []

        # 1. Linguistic consistency
        lengths = posts_df['post_text'].str.len()
        avg_len = lengths.mean()
        std_len = lengths.std()
        if avg_len > 0 and std_len > 0:
            linguistic_risk = min(100, max(0, (1 - (std_len / avg_len)) * 100))
        else:
            linguistic_risk = 50.0
        risk_scores.append(linguistic_risk * 0.25)

        # 2. Posting interval consistency
        if len(posts_df) > 1:
            sorted_df = posts_df.sort_values('post_date')
            diffs = sorted_df['post_date'].diff().dt.total_seconds().div(3600).dropna()
            if len(diffs) > 0 and diffs.mean() > 0:
                interval_risk = min(100, max(0,
                    (1 - (diffs.std() / (diffs.mean() + 1))) * 100
                ))
            else:
                interval_risk = 50.0
        else:
            interval_risk = 0.0
        risk_scores.append(interval_risk * 0.20)

        # 3. Content diversity (low ratio = repetitive = higher risk)
        all_words = ' '.join(posts_df['post_text'].astype(str)).lower().split()
        total_words = len(all_words)
        if total_words > 0:
            diversity_ratio = len(set(all_words)) / total_words
            diversity_risk = min(100, max(0, (1 - diversity_ratio) * 100))
        else:
            diversity_risk = 50.0
        risk_scores.append(diversity_risk * 0.20)

        # 4. Engagement consistency
        if len(posts_df) > 1:
            engagement = posts_df['likes'] + posts_df['comments']
            avg_eng = engagement.mean()
            std_eng = engagement.std()
            if avg_eng > 0:
                engagement_risk = min(100, max(0,
                    (1 - (std_eng / (avg_eng + 1))) * 100
                ))
            else:
                engagement_risk = 0.0
        else:
            engagement_risk = 0.0
        risk_scores.append(engagement_risk * 0.20)

        # 5. Account metrics
        account_age  = profile_data.get('account_age_days', 365)
        followers    = profile_data.get('followers_count', 0)
        following    = profile_data.get('following_count', 1)
        ratio        = followers / (following + 1)

        age_risk      = 60 if account_age < 90 else 30 if account_age < 180 else 0
        follower_risk = 40 if ratio > 5 else 20 if ratio > 1 else 0
        risk_scores.append(((age_risk + follower_risk) / 2) * 0.15)

        return min(100.0, max(0.0, sum(risk_scores)))

    @staticmethod
    def calculate_fake_profile_risk(posts_df, profile_data) -> float:
        """
        Fake/compromised profile risk (0–100).

        Factors and weights:
          30% — Follower/following ratio
          20% — Bio quality
          20% — Account age
          20% — Posting frequency
          10% — Sudden behavior change
        """
        if posts_df is None:
            return 0.0

        risk_scores = []

        # 1. Follower/following ratio
        followers = profile_data.get('followers_count', 0)
        following = profile_data.get('following_count', 1)
        ratio     = followers / (following + 1)
        follower_risk = 70 if ratio > 10 else 50 if ratio > 5 else 20 if ratio > 1 else 0
        risk_scores.append(follower_risk * 0.30)

        # 2. Bio quality
        bio      = str(profile_data.get('bio', ''))
        bio_len  = len(bio.strip())
        bio_risk = 60 if bio_len < 10 else 30 if bio_len < 50 else 0
        risk_scores.append(bio_risk * 0.20)

        # 3. Account age
        account_age = profile_data.get('account_age_days', 365)
        age_risk    = 80 if account_age < 30 else 50 if account_age < 90 else 20 if account_age < 180 else 0
        risk_scores.append(age_risk * 0.20)

        # 4. Posting frequency
        if len(posts_df) > 0:
            posts_per_day = len(posts_df) / max(account_age, 1)
            freq_risk = 70 if posts_per_day > 5 else 40 if posts_per_day > 2 else 10 if posts_per_day > 0.1 else 0
        else:
            freq_risk = 40
        risk_scores.append(freq_risk * 0.20)

        # 5. Sudden behavior change (post length shift between halves)
        behavior_risk = 0.0
        if len(posts_df) > 2:
            sorted_df  = posts_df.sort_values('post_date')
            mid        = len(sorted_df) // 2
            first_avg  = sorted_df.head(mid)['post_text'].str.len().mean()
            second_avg = sorted_df.tail(mid)['post_text'].str.len().mean()
            change     = abs(first_avg - second_avg) / (first_avg + 1) * 100
            behavior_risk = 60 if change > 50 else 30 if change > 25 else 0
        risk_scores.append(behavior_risk * 0.10)

        return min(100.0, max(0.0, sum(risk_scores)))

    @staticmethod
    def calculate_account_takeover_risk(posts_df) -> float:
        """
        Account takeover risk (0–100).

        Factors and weights:
          40% — Language/length change between early and late posts
          30% — Engagement pattern change
          30% — Posting frequency change
        """
        if posts_df is None or len(posts_df) < 3:
            return 0.0

        risk_scores  = []
        sorted_df    = posts_df.sort_values('post_date')
        third        = len(sorted_df) // 3
        first_third  = sorted_df.head(third)
        last_third   = sorted_df.tail(third)

        if len(first_third) == 0 or len(last_third) == 0:
            return 0.0

        # 1. Language change
        first_len = first_third['post_text'].str.len().mean()
        last_len  = last_third['post_text'].str.len().mean()
        lang_change = abs(first_len - last_len) / (first_len + 1) * 100
        lang_risk   = 70 if lang_change > 40 else 40 if lang_change > 20 else 10
        risk_scores.append(lang_risk * 0.40)

        # 2. Engagement change
        first_eng = first_third['likes'].mean() + first_third['comments'].mean()
        last_eng  = last_third['likes'].mean()  + last_third['comments'].mean()
        eng_change = abs(first_eng - last_eng) / (first_eng + 1) * 100
        eng_risk   = 60 if eng_change > 50 else 30 if eng_change > 25 else 10
        risk_scores.append(eng_risk * 0.30)

        # 3. Posting frequency change
        freq_risk = 0
        mid       = len(sorted_df) // 2
        first_half = sorted_df.head(mid)['post_date']
        last_half  = sorted_df.tail(mid)['post_date']

        if len(first_half) > 1 and len(last_half) > 1:
            first_span = max((first_half.max() - first_half.min()).days, 1)
            last_span  = max((last_half.max()  - last_half.min()).days,  1)
            first_freq = len(first_half) / first_span
            last_freq  = len(last_half)  / last_span
            freq_change = abs(first_freq - last_freq) / (first_freq + 0.1) * 100
            freq_risk   = 60 if freq_change > 100 else 40 if freq_change > 50 else 10
        risk_scores.append(freq_risk * 0.30)

        return min(100.0, max(0.0, sum(risk_scores)))

    @staticmethod
    def calculate_overall_risk(
        ai_risk: float,
        fake_risk: float,
        extremism_score: float,
        toxicity_score: float,
        misinformation_score: float
    ) -> float:
        """
        Overall risk score (0–100).

        Weights:
          35% — AI/bot profile risk
          35% — Fake profile risk
          30% — Worst content score (extremism, toxicity, or misinformation)
        """
        worst_content = max(extremism_score, toxicity_score, misinformation_score)
        overall = (ai_risk * 0.35) + (fake_risk * 0.35) + (worst_content * 0.30)
        return min(100.0, max(0.0, overall))

    @staticmethod
    def analyze_profile(posts_df, profile_data) -> dict:
        """
        Full profile-level analysis. Expects posts_df to already contain
        per-post scores (populated by analyze_post during ingestion).
        Returns all risk scores as a dict.
        """
        ai_risk       = Analyzer.calculate_ai_profile_risk(posts_df, profile_data)
        fake_risk     = Analyzer.calculate_fake_profile_risk(posts_df, profile_data)
        takeover_risk = Analyzer.calculate_account_takeover_risk(posts_df)

        def col_mean(col):
            return float(posts_df[col].mean()) if col in posts_df.columns and len(posts_df) > 0 else 0.0

        extremism_score      = col_mean('extremism_score')
        toxicity_score       = col_mean('toxicity_score')
        misinformation_score = col_mean('misinformation_score')

        overall_risk = Analyzer.calculate_overall_risk(
            ai_risk, fake_risk, extremism_score, toxicity_score, misinformation_score
        )

        return {
            'ai_profile_risk':      ai_risk,
            'fake_profile_risk':    fake_risk,
            'account_takeover_risk':takeover_risk,
            'overall_risk':         overall_risk,
            'extremism_score':      extremism_score,
            'toxicity_score':       toxicity_score,
            'misinformation_score': misinformation_score,
        }