"""Sentiment Analyzer — Lexicon-based sentiment analysis for scraped text data.
No external API required, works offline with Indonesian + English dictionaries."""
import re
from collections import Counter
from dataclasses import dataclass, field


INDONESIAN_POSITIVE = {
    "bagus", "baik", "suka", "senang", "puas", "hebat", "luar biasa", "sempurna",
    "cantik", "indah", "cantik", "menarik", "unggul", "terbaik", "mudah", "cepat",
    "gratis", "mudah", "aman", "nyaman", "efisien", "praktis", "inovatif", "modern",
    "berhasil", "sukses", "untung", "hemat", "berkualitas", "recommended", "top",
    "mantap", "joss", "keren", "wah", "oke", "ok", "sip", "jaya", "mulia",
    "positif", "optimis", "semangat", "antusias", "setia", "loyal", "jujur",
    "adil", "murah", "lengkap", "canggih", "pintar", "cerdas", "unggul",
    "pujian", "terima kasih", "makasih", "thanks", "appreciate", "love",
    "good", "great", "excellent", "amazing", "wonderful", "fantastic",
    "perfect", "best", "awesome", "brilliant", "superb", "outstanding",
    "nice", "beautiful", "happy", "pleased", "satisfied", "impressed",
    "recommend", "worth", "easy", "fast", "efficient", "reliable", "helpful",
}

INDONESIAN_NEGATIVE = {
    "jelek", "buruk", "benci", "kesal", "marah", "kecewa", "gagal", "rusak",
    "lambat", "sulit", "rumit", "mahal", "jelek", "hancur", "lemah", "lemot",
    "parah", "kotor", "bermasalah", "error", "bug", "crash", "tidak", "bukan",
    "nyesel", "rugi", "tipu", "scam", "penipuan", "bohong", "palsu", "abal",
    "sampah", "tai", "bangsat", "kntl", "anjing", "goblok", "bodoh", "tolol",
    "negatif", "pesimis", "lesu", "malas", "sakit", "sengsara", "menderita",
    "miskin", "gelandangan", "kumuh", "kumuh", "jorok", "bau", "kotor",
    "poor", "bad", "terrible", "horrible", "awful", "worst", "hate",
    "disappointed", "frustrated", "angry", "annoyed", "broken", "useless",
    "waste", "scam", "fake", "fake", "spam", "annoying", "slow", "ugly",
    "fail", "failed", "failure", "problem", "issue", "bug", "crash", "error",
}

INDONESIAN_INTENSIFIERS = {
    "sangat", "sekali", "banget", "amat", "paling", "super", "ultra",
    "extra", "really", "very", "extremely", "incredibly", "absolutely",
}

INDONESIAN_NEGATORS = {
    "tidak", "bukan", "jangan", "belum", "tak", "tanpa", "tiada",
    "no", "not", "never", "neither", "nor", "barely", "hardly", "scarcely",
}

INDONESIAN_EMOJI_SENTIMENT = {
    "😀": 0.5, "😃": 0.5, "😄": 0.5, "😁": 0.5, "😆": 0.5,
    "😊": 0.5, "😍": 0.7, "🥰": 0.7, "😘": 0.5, "😎": 0.4,
    "🤩": 0.6, "🥳": 0.6, "👍": 0.4, "👏": 0.5, "🎉": 0.5,
    "💪": 0.4, "❤️": 0.6, "💯": 0.5, "⭐": 0.4, "🔥": 0.4,
    "😢": -0.4, "😭": -0.5, "😡": -0.6, "🤬": -0.7, "😤": -0.5,
    "👎": -0.4, "😠": -0.5, "💔": -0.5, "🤮": -0.6, "💀": -0.3,
    "😱": -0.4, "😰": -0.3, "😨": -0.4, "😒": -0.3, "🙄": -0.2,
    "😕": -0.2, "😟": -0.3, "😞": -0.4, "😔": -0.3,
}


@dataclass
class SentimentResult:
    text: str
    score: float = 0.0
    label: str = "neutral"
    confidence: float = 0.0
    positive_words: list = field(default_factory=list)
    negative_words: list = field(default_factory=list)
    emoji_sentiment: list = field(default_factory=list)
    word_count: int = 0
    sentence_count: int = 0

    def to_dict(self) -> dict:
        return {
            "text": self.text[:200],
            "score": round(self.score, 4),
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "positive_words": self.positive_words[:10],
            "negative_words": self.negative_words[:10],
            "emoji_sentiment": self.emoji_sentiment[:5],
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
        }


@dataclass
class SentimentAnalysis:
    overall_score: float = 0.0
    overall_label: str = "neutral"
    total_texts: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    distribution: dict = field(default_factory=dict)
    top_positive_words: list = field(default_factory=list)
    top_negative_words: list = field(default_factory=list)
    avg_confidence: float = 0.0
    sentiment_timeline: list = field(default_factory=list)
    column_sentiments: dict = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 4),
            "overall_label": self.overall_label,
            "total_texts": self.total_texts,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "distribution": self.distribution,
            "top_positive_words": self.top_positive_words[:10],
            "top_negative_words": self.top_negative_words[:10],
            "avg_confidence": round(self.avg_confidence, 4),
            "column_sentiments": self.column_sentiments,
            "summary": self.summary,
        }


class SentimentAnalyzer:

    def __init__(self):
        self._positive = INDONESIAN_POSITIVE
        self._negative = INDONESIAN_NEGATIVE
        self._intensifiers = INDONESIAN_INTENSIFIERS
        self._negators = INDONESIAN_NEGATORS

    def analyze_text(self, text: str) -> SentimentResult:
        result = SentimentResult(text=text[:500])
        if not text or not text.strip():
            return result

        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        result.word_count = len(words)
        result.sentence_count = max(len(re.split(r'[.!?]+', text)), 1)

        positive_found = []
        negative_found = []
        for w in words:
            if w in self._positive:
                positive_found.append(w)
            elif w in self._negative:
                negative_found.append(w)

        pos_score = len(positive_found) * 1.0
        neg_score = len(negative_found) * 1.0

        negated = False
        intensifier = 1.0
        for i, w in enumerate(words):
            if w in self._negators:
                negated = True
                continue
            if w in self._intensifiers:
                intensifier = 1.5
                continue
            if negated:
                if w in self._positive:
                    neg_score += 1.0
                    pos_score -= 0.5
                elif w in self._negative:
                    pos_score += 1.0
                    neg_score -= 0.5
                negated = False
            if intensifier > 1.0:
                if w in self._positive:
                    pos_score *= intensifier
                elif w in self._negative:
                    neg_score *= intensifier
                intensifier = 1.0

        emoji_score = 0.0
        emojis_found = []
        for char in text:
            if char in INDONESIAN_EMOJI_SENTIMENT:
                emoji_score += INDONESIAN_EMOJI_SENTIMENT[char]
                emojis_found.append(char)
        if emojis_found:
            emoji_score /= len(emojis_found)

        total = pos_score + neg_score
        if total > 0:
            result.score = (pos_score - neg_score) / total
        if emojis_found:
            result.score = result.score * 0.7 + emoji_score * 0.3

        if result.score > 0.15:
            result.label = "positive"
        elif result.score < -0.15:
            result.label = "negative"
        else:
            result.label = "neutral"

        result.confidence = min(abs(result.score) + (len(positive_found) + len(negative_found)) / max(len(words), 1) * 0.5, 1.0)
        result.positive_words = list(set(positive_found))
        result.negative_words = list(set(negative_found))
        result.emoji_sentiment = [{"emoji": e, "score": INDONESIAN_EMOJI_SENTIMENT.get(e, 0)} for e in set(emojis_found)]

        return result

    def analyze_dataframe(self, df, text_columns: list[str] = None) -> SentimentAnalysis:
        analysis = SentimentAnalysis()
        if text_columns is None:
            text_columns = []
            for col in df.columns:
                if pd.api.types.is_string_dtype(df[col]):
                    sample = df[col].dropna().head(50)
                    if len(sample) > 0 and sample.astype(str).str.len().mean() > 15:
                        text_columns.append(col)

        if not text_columns:
            analysis.summary = "Tidak ada kolom teks yang cukup panjang untuk analisis sentimen."
            return analysis

        all_positive = []
        all_negative = []
        scores = []
        confidences = []

        for col in text_columns:
            col_results = []
            series = df[col].dropna().astype(str).head(500)
            for text in series:
                result = self.analyze_text(text)
                scores.append(result.score)
                confidences.append(result.confidence)
                col_results.append(result.score)
                all_positive.extend(result.positive_words)
                all_negative.extend(result.negative_words)

                if result.label == "positive":
                    analysis.positive_count += 1
                elif result.label == "negative":
                    analysis.negative_count += 1
                else:
                    analysis.neutral_count += 1

            analysis.column_sentiments[col] = {
                "avg_score": round(float(sum(col_results) / max(len(col_results), 1)), 4),
                "distribution": {
                    "positive": sum(1 for s in col_results if s > 0.15),
                    "negative": sum(1 for s in col_results if s < -0.15),
                    "neutral": sum(1 for s in col_results if -0.15 <= s <= 0.15),
                },
                "sample_size": len(col_results),
            }

        analysis.total_texts = analysis.positive_count + analysis.negative_count + analysis.neutral_count
        if scores:
            analysis.overall_score = round(float(sum(scores) / len(scores)), 4)
        if confidences:
            analysis.avg_confidence = round(float(sum(confidences) / len(confidences)), 4)

        if analysis.overall_score > 0.15:
            analysis.overall_label = "positive"
        elif analysis.overall_score < -0.15:
            analysis.overall_label = "negative"
        else:
            analysis.overall_label = "neutral"

        pos_counter = Counter(all_positive).most_common(15)
        neg_counter = Counter(all_negative).most_common(15)
        analysis.top_positive_words = [{"word": w, "count": c} for w, c in pos_counter]
        analysis.top_negative_words = [{"word": w, "count": c} for w, c in neg_counter]

        total = max(analysis.total_texts, 1)
        analysis.distribution = {
            "positive_pct": round(analysis.positive_count / total * 100, 2),
            "negative_pct": round(analysis.negative_count / total * 100, 2),
            "neutral_pct": round(analysis.neutral_count / total * 100, 2),
        }

        analysis.summary = (
            f"Analisis sentimen dari {analysis.total_texts} teks: "
            f"{analysis.distribution['positive_pct']}% positif, "
            f"{analysis.distribution['negative_pct']}% negatif, "
            f"{analysis.distribution['neutral_pct']}% netral. "
            f"Skor rata-rata: {analysis.overall_score:.2f} ({analysis.overall_label})."
        )
        return analysis
