from app.utils.text_normalizer import TextComparator, TextNormalizer


class TestTextNormalizer:
    def test_normalize_basic(self):
        assert TextNormalizer.normalize("Olá Mundo") == "ola mundo"
        assert TextNormalizer.normalize("TERÇA-FEIRA") == "terca feira"
        assert TextNormalizer.normalize("  extra  spaces  ") == "extra spaces"
        assert TextNormalizer.normalize("") == ""
        assert TextNormalizer.normalize(None) == ""

    def test_similarity(self):
        # Identical strings
        assert TextNormalizer.similarity("ola mundo", "ola mundo") == 1.0
        # Completely different
        assert TextNormalizer.similarity("ola", "tchau") == 0.0
        # Partial similarity
        sim = TextNormalizer.similarity("ola mundo", "ola")
        assert 0 < sim < 1


class TestTextComparator:
    def setup_method(self):
        self.comp = TextComparator()

    def test_similarity_identical(self):
        assert self.comp.similarity("olá mundo", "olá mundo") == 1.0

    def test_similarity_case_insensitive(self):
        assert self.comp.similarity("OLÁ MUNDO", "olá mundo") == 1.0

    def test_similarity_accents_normalized(self):
        assert self.comp.similarity("terça-feira", "terca feira") == 1.0

    def test_token_coverage_full(self):
        assert self.comp.token_coverage("olá mundo", "olá mundo") == 1.0

    def test_token_coverage_partial(self):
        # "olá" covers 1 of 2 words in script
        assert self.comp.token_coverage("olá", "olá mundo") == 0.5

    def test_token_coverage_no_match(self):
        assert self.comp.token_coverage("tchau", "olá mundo") == 0.0

    def test_relevant_word_score_exact(self):
        # Weak words filtered out
        score = self.comp.relevant_word_score("o apresentador disse", "apresentador disse")
        assert score == 1.0

    def test_relevant_word_score_fuzzy(self):
        # Similar words match at 0.72 threshold
        score = self.comp.relevant_word_score("apresentadór", "apresentador")
        assert score > 0.5

    def test_has_relevant_word_match_true(self):
        assert self.comp.has_relevant_word_match("apresentador disse", "o apresentador falou")

    def test_has_relevant_word_match_false(self):
        assert not self.comp.has_relevant_word_match("tchau", "olá mundo")

    def test_is_noise_empty(self):
        assert self.comp.is_noise("", "olá mundo")

    def test_is_noise_short(self):
        assert self.comp.is_noise("oi", "olá mundo")

    def test_is_noise_single_word_no_match(self):
        assert self.comp.is_noise("xyz", "olá mundo")

    def test_is_noise_single_word_match(self):
        assert not self.comp.is_noise("apresentador", "o apresentador falou")

    def test_weighted_score_identical(self):
        score, sim, cov, rel = self.comp.weighted_score("olá mundo", "olá mundo")
        assert score == 1.0
        assert sim == 1.0
        assert cov == 1.0
        assert rel == 1.0

    def test_weighted_score_no_match(self):
        score, _sim, _cov, _rel = self.comp.weighted_score("tchau", "olá mundo")
        assert score == 0.0


class TestRapidFuzzPerformance:
    """Basic sanity check that rapidfuzz is working and fast."""
    
    def test_fuzz_imported(self):
        from rapidfuzz import fuzz
        assert fuzz.ratio("test", "test") == 100
        assert fuzz.ratio("test", "tent") > 0
