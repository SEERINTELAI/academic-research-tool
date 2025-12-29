"""
Intent Parser Service

Parses user messages into structured intents for the research agent.
Extracts paper references, action types, and parameters.
"""

import re
import logging
from typing import Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

IntentType = Literal[
    "search",           # Search for papers on a topic
    "deepen",           # Find more papers like specific ones
    "summarize",        # Summarize a paper or set of papers
    "generate_outline", # Generate outline from found papers
    "add_section",      # Add a section to the outline
    "edit_section",     # Edit an existing section
    "link_source",      # Link a paper to a claim
    "find_gaps",        # Identify claims that need more sources
    "ask_question",     # Ask a question about the research
    "unknown",          # Could not determine intent
]


class Intent(BaseModel):
    """Structured representation of user intent."""
    
    type: IntentType
    query: str | None = None
    paper_refs: list[int] = Field(default_factory=list)  # Indices like [1, 5, 7]
    section_ref: str | None = None  # Section number or title
    claim_ref: str | None = None    # Claim identifier
    raw_message: str = ""           # Original user message
    confidence: float = 0.8         # How confident we are in the parse


# Patterns for extracting paper references
PAPER_REF_PATTERNS = [
    r"papers?\s*#?\s*(\d+(?:\s*,\s*\d+)*(?:\s*(?:and|&)\s*\d+)?)",  # "papers 1, 2, and 3" or "paper #5"
    r"#(\d+)",  # "#5"
    r"papers?\s+(\d+)\s+(?:and|&)\s+(\d+)",  # "papers 5 and 7"
    r"\[(\d+(?:\s*,\s*\d+)*)\]",  # "[1, 2, 3]"
]

# Keywords that indicate specific intents
INTENT_KEYWORDS = {
    "search": [
        "search", "find", "look for", "look up", "get papers", "fetch",
        "papers on", "papers about", "research on", "articles about",
    ],
    "deepen": [
        "more like", "similar to", "related to", "go deeper", "expand on",
        "find more", "like this", "like these", "like paper", "like papers",
        "by this author", "by these authors", "same author", "same topic",
    ],
    "summarize": [
        "summarize", "summary", "what does", "what is", "tell me about",
        "explain", "describe", "overview of",
    ],
    "generate_outline": [
        "generate outline", "generate an outline", "create outline", "create an outline",
        "make outline", "make an outline", "build outline", "build an outline",
        "outline from", "draft outline", "suggest outline", "start outline",
        "write outline", "write an outline", "outline based on", "create the outline",
    ],
    "add_section": [
        "add section", "new section", "add a section", "include section",
        "add topic", "add chapter",
    ],
    "edit_section": [
        "edit section", "modify section", "change section", "update section",
        "rename section", "revise section",
    ],
    "link_source": [
        "link paper", "link source", "add paper to", "cite paper",
        "use paper", "connect paper", "support claim", "add citation",
    ],
    "find_gaps": [
        "gaps", "missing sources", "need more", "needs sources",
        "unsupported claims", "weak claims", "which claims",
    ],
    "ask_question": [
        "what", "how", "why", "when", "where", "who", "which",
        "can you", "could you", "would you", "is there", "are there",
    ],
}


def extract_paper_refs(message: str) -> list[int]:
    """Extract paper reference numbers from a message."""
    refs: set[int] = set()
    message_lower = message.lower()
    
    for pattern in PAPER_REF_PATTERNS:
        matches = re.findall(pattern, message_lower)
        for match in matches:
            if isinstance(match, tuple):
                # Multiple groups matched
                for group in match:
                    if group:
                        for num_str in re.findall(r"\d+", group):
                            refs.add(int(num_str))
            else:
                # Single group
                for num_str in re.findall(r"\d+", match):
                    refs.add(int(num_str))
    
    return sorted(refs)


def extract_section_ref(message: str) -> str | None:
    """Extract section reference from a message."""
    # Look for patterns like "section 2", "section on Methods", "the introduction"
    patterns = [
        r"section\s+(\d+|[a-zA-Z]+(?:\s+[a-zA-Z]+)*)",
        r"the\s+(introduction|conclusion|methods?|results?|discussion|abstract)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            return match.group(1)
    
    return None


def detect_intent_type(message: str, paper_refs: list[int]) -> tuple[IntentType, float]:
    """Detect the primary intent type from a message."""
    message_lower = message.lower()
    
    # Score each intent type based on keyword matches
    scores: dict[IntentType, float] = {intent: 0.0 for intent in INTENT_KEYWORDS}
    
    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                # Longer keywords get higher scores (more specific)
                scores[intent] += len(keyword.split()) * 0.3
    
    # Boost deepen if paper references are present
    if paper_refs and scores["deepen"] > 0:
        scores["deepen"] += 0.5
    
    # Find the highest scoring intent
    max_score = max(scores.values())
    if max_score < 0.3:
        return "unknown", 0.3
    
    best_intent = max(scores.items(), key=lambda x: x[1])[0]
    confidence = min(0.95, 0.5 + max_score * 0.3)
    
    return best_intent, confidence


def extract_query(message: str, intent_type: IntentType) -> str | None:
    """Extract the main query/topic from a message."""
    message_clean = message.strip()
    
    # Remove paper references for cleaner query extraction
    for pattern in PAPER_REF_PATTERNS:
        message_clean = re.sub(pattern, "", message_clean, flags=re.IGNORECASE)
    
    # Remove common command prefixes
    prefixes_to_remove = [
        r"^(please\s+)?",
        r"^can\s+you\s+",
        r"^could\s+you\s+",
        r"^search\s+for\s+",
        r"^find\s+",
        r"^look\s+for\s+",
        r"^get\s+papers?\s+(?:on|about)\s+",
    ]
    
    for prefix in prefixes_to_remove:
        message_clean = re.sub(prefix, "", message_clean, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    message_clean = " ".join(message_clean.split())
    
    if len(message_clean) < 3:
        return None
    
    return message_clean


def parse_intent(message: str) -> Intent:
    """
    Parse a user message into a structured Intent.
    
    Examples:
        "search for quantum cryptography"
        -> Intent(type="search", query="quantum cryptography")
        
        "papers 3 and 7 look interesting, find more like them"
        -> Intent(type="deepen", paper_refs=[3, 7])
        
        "generate an outline from what we've found"
        -> Intent(type="generate_outline")
        
        "link paper #5 to section 2"
        -> Intent(type="link_source", paper_refs=[5], section_ref="2")
    """
    if not message or not message.strip():
        return Intent(type="unknown", raw_message=message, confidence=0.0)
    
    # Extract paper references
    paper_refs = extract_paper_refs(message)
    
    # Detect intent type
    intent_type, confidence = detect_intent_type(message, paper_refs)
    
    # Extract query
    query = extract_query(message, intent_type)
    
    # Extract section reference if relevant
    section_ref = None
    if intent_type in ("link_source", "add_section", "edit_section"):
        section_ref = extract_section_ref(message)
    
    return Intent(
        type=intent_type,
        query=query,
        paper_refs=paper_refs,
        section_ref=section_ref,
        raw_message=message,
        confidence=confidence,
    )


# Convenience function for testing
def describe_intent(intent: Intent) -> str:
    """Generate a human-readable description of an intent."""
    parts = [f"Intent: {intent.type}"]
    
    if intent.query:
        parts.append(f"Query: '{intent.query}'")
    if intent.paper_refs:
        parts.append(f"Papers: {intent.paper_refs}")
    if intent.section_ref:
        parts.append(f"Section: {intent.section_ref}")
    
    parts.append(f"Confidence: {intent.confidence:.0%}")
    
    return " | ".join(parts)

