"""
Unit tests for the intent parser service.
"""

import pytest
from src.services.intent_parser import (
    extract_paper_refs,
    detect_intent_type,
    extract_section_ref,
    extract_query,
    parse_intent,
    describe_intent,
)


class TestExtractPaperRefs:
    """Tests for paper reference extraction."""

    def test_extract_single_paper_hash(self):
        """Extract #5 format."""
        refs = extract_paper_refs("Look at paper #5")
        assert refs == [5]

    def test_extract_multiple_papers_comma(self):
        """Extract papers 1, 2, 3 format."""
        refs = extract_paper_refs("papers 1, 2, 3 are interesting")
        assert refs == [1, 2, 3]

    def test_extract_papers_with_and(self):
        """Extract papers 3 and 7 format."""
        refs = extract_paper_refs("papers 3 and 7 look related")
        assert refs == [3, 7]

    def test_extract_bracket_format(self):
        """Extract [1, 2, 3] format."""
        refs = extract_paper_refs("See references [1, 2, 3]")
        assert refs == [1, 2, 3]

    def test_extract_mixed_formats(self):
        """Extract mixed reference formats."""
        refs = extract_paper_refs("paper #5 and papers 3, 7 are good")
        assert sorted(refs) == [3, 5, 7]

    def test_no_refs(self):
        """No paper references found."""
        refs = extract_paper_refs("search for quantum computing")
        assert refs == []

    def test_single_digit_paper(self):
        """Single digit paper number."""
        refs = extract_paper_refs("paper 1")
        assert refs == [1]


class TestDetectIntentType:
    """Tests for intent type detection."""

    def test_detect_search_intent(self):
        """Detect search intent."""
        intent_type, confidence = detect_intent_type("search for quantum cryptography", [])
        assert intent_type == "search"
        assert confidence > 0.5

    def test_detect_find_papers_intent(self):
        """Detect find papers intent as search."""
        intent_type, _ = detect_intent_type("find papers on machine learning", [])
        assert intent_type == "search"

    def test_detect_deepen_intent(self):
        """Detect deepen intent with paper refs."""
        intent_type, _ = detect_intent_type("find more like these papers", [1, 2])
        assert intent_type == "deepen"

    def test_detect_summarize_intent(self):
        """Detect summarize intent."""
        intent_type, _ = detect_intent_type("summarize the key findings", [])
        assert intent_type == "summarize"

    def test_detect_outline_intent(self):
        """Detect generate outline intent."""
        intent_type, _ = detect_intent_type("create an outline from what we found", [])
        assert intent_type == "generate_outline"

    def test_detect_add_section_intent(self):
        """Detect add section intent."""
        intent_type, _ = detect_intent_type("add a section on methodology", [])
        assert intent_type == "add_section"

    def test_detect_link_source_intent(self):
        """Detect link source intent."""
        intent_type, _ = detect_intent_type("link paper 5 to section 2", [5])
        assert intent_type == "link_source"

    def test_detect_find_gaps_intent(self):
        """Detect find gaps intent."""
        intent_type, _ = detect_intent_type("which claims need more sources?", [])
        assert intent_type == "find_gaps"

    def test_detect_unknown_intent(self):
        """Unknown intent for ambiguous messages."""
        intent_type, confidence = detect_intent_type("hello there", [])
        assert intent_type == "unknown"
        assert confidence < 0.5


class TestExtractSectionRef:
    """Tests for section reference extraction."""

    def test_extract_section_number(self):
        """Extract section number."""
        ref = extract_section_ref("add to section 2")
        assert ref == "2"

    def test_extract_section_name(self):
        """Extract section name."""
        ref = extract_section_ref("section on Methods")
        assert ref is not None
        assert "methods" in ref.lower()

    def test_extract_introduction(self):
        """Extract 'the introduction'."""
        ref = extract_section_ref("add to the introduction")
        assert ref == "introduction"

    def test_no_section_ref(self):
        """No section reference."""
        ref = extract_section_ref("search for papers")
        assert ref is None


class TestExtractQuery:
    """Tests for query extraction."""

    def test_extract_search_query(self):
        """Extract query from search message."""
        query = extract_query("search for quantum cryptography", "search")
        assert query is not None
        assert "quantum cryptography" in query.lower()

    def test_extract_with_prefix(self):
        """Extract query with command prefix."""
        query = extract_query("please find papers on machine learning", "search")
        assert query is not None
        assert "machine learning" in query.lower()

    def test_empty_after_cleaning(self):
        """Return None for very short results."""
        query = extract_query("search", "search")
        # Query should be None or very short
        assert query is None or len(query) < 3


class TestParseIntent:
    """Tests for full intent parsing."""

    def test_parse_search_intent(self):
        """Parse a search message."""
        intent = parse_intent("search for quantum cryptography")
        assert intent.type == "search"
        assert "quantum" in (intent.query or "").lower()
        assert intent.paper_refs == []

    def test_parse_deepen_with_refs(self):
        """Parse a deepen message with paper references."""
        intent = parse_intent("papers 3 and 7 look interesting, find more like them")
        assert intent.type == "deepen"
        assert 3 in intent.paper_refs
        assert 7 in intent.paper_refs

    def test_parse_outline_generation(self):
        """Parse outline generation message."""
        intent = parse_intent("generate an outline from what we've found")
        assert intent.type == "generate_outline"

    def test_parse_link_source(self):
        """Parse link source message."""
        intent = parse_intent("link paper #5 to section 2")
        assert intent.type == "link_source"
        assert 5 in intent.paper_refs
        assert intent.section_ref == "2"

    def test_parse_empty_message(self):
        """Handle empty message."""
        intent = parse_intent("")
        assert intent.type == "unknown"
        assert intent.confidence == 0.0

    def test_preserves_raw_message(self):
        """Raw message is preserved."""
        msg = "search for quantum computing"
        intent = parse_intent(msg)
        assert intent.raw_message == msg


class TestDescribeIntent:
    """Tests for intent description."""

    def test_describe_search_intent(self):
        """Describe a search intent."""
        intent = parse_intent("search for quantum cryptography")
        desc = describe_intent(intent)
        assert "search" in desc.lower()
        assert "quantum" in desc.lower()

    def test_describe_with_paper_refs(self):
        """Describe intent with paper references."""
        intent = parse_intent("papers 3, 5 are good")
        desc = describe_intent(intent)
        assert "3" in desc
        assert "5" in desc

