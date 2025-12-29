"""
Topic Classification Service.

Uses AI to classify papers into topic groups for the Library tab.
"""

import logging
import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.config import get_settings

logger = logging.getLogger(__name__)


class TopicClassification(BaseModel):
    """Result of topic classification."""
    topic: str = Field(..., description="The classified topic name")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    reasoning: Optional[str] = Field(None, description="Why this topic was chosen")


class TopicClassifierService:
    """
    Classifies academic papers into topics using AI.
    
    Uses simple keyword/heuristic classification with optional AI enhancement.
    Topics are meant to group papers in a Zotero-like library view.
    """
    
    # Common academic topic patterns
    TOPIC_PATTERNS = {
        "Machine Learning": [
            r"machine\s+learning", r"deep\s+learning", r"neural\s+network",
            r"reinforcement\s+learning", r"supervised\s+learning", r"transformer",
            r"convolutional", r"recurrent", r"attention\s+mechanism", r"bert",
            r"gpt", r"llm", r"language\s+model", r"classification", r"regression"
        ],
        "Natural Language Processing": [
            r"natural\s+language", r"nlp", r"text\s+mining", r"sentiment\s+analysis",
            r"named\s+entity", r"parsing", r"machine\s+translation", r"summarization",
            r"question\s+answering", r"chatbot", r"dialogue"
        ],
        "Computer Vision": [
            r"computer\s+vision", r"image\s+recognition", r"object\s+detection",
            r"image\s+segmentation", r"face\s+recognition", r"video\s+analysis",
            r"convolutional\s+neural", r"visual", r"opencv"
        ],
        "Quantum Computing": [
            r"quantum\s+comput", r"quantum\s+algorithm", r"qubit", r"quantum\s+circuit",
            r"quantum\s+supremacy", r"quantum\s+error", r"quantum\s+machine\s+learning"
        ],
        "Cryptography & Security": [
            r"cryptograph", r"encryption", r"security", r"privacy", r"authentication",
            r"blockchain", r"cyber", r"malware", r"intrusion", r"post-quantum"
        ],
        "Data Science & Analytics": [
            r"data\s+science", r"big\s+data", r"data\s+mining", r"analytics",
            r"visualization", r"statistics", r"predictive", r"data\s+processing"
        ],
        "Robotics & Control": [
            r"robot", r"control\s+system", r"autonomous", r"navigation",
            r"sensor", r"actuator", r"motion\s+planning", r"manipulation"
        ],
        "Bioinformatics": [
            r"bioinformatics", r"genomic", r"protein", r"dna", r"rna",
            r"sequence\s+analysis", r"molecular", r"drug\s+discovery"
        ],
        "Networks & Distributed Systems": [
            r"network", r"distributed", r"cloud\s+computing", r"edge\s+computing",
            r"iot", r"wireless", r"protocol", r"peer-to-peer", r"consensus"
        ],
        "Software Engineering": [
            r"software\s+engineering", r"code\s+generation", r"testing",
            r"debugging", r"refactoring", r"version\s+control", r"devops"
        ],
    }
    
    def __init__(self):
        """Initialize the topic classifier."""
        self.settings = get_settings()
    
    async def classify(
        self,
        title: str,
        abstract: Optional[str] = None,
        use_ai: bool = False,
    ) -> TopicClassification:
        """
        Classify a paper into a topic.
        
        Args:
            title: Paper title
            abstract: Paper abstract (optional but improves accuracy)
            use_ai: Whether to use AI for classification (slower but more accurate)
            
        Returns:
            TopicClassification with topic name and confidence
        """
        text = f"{title} {abstract or ''}".lower()
        
        # Try pattern-based classification first
        result = self._pattern_classify(text)
        
        if result.confidence >= 0.7:
            return result
        
        # If low confidence and AI is enabled, try AI classification
        if use_ai and result.confidence < 0.5:
            ai_result = await self._ai_classify(title, abstract)
            if ai_result and ai_result.confidence > result.confidence:
                return ai_result
        
        return result
    
    def _pattern_classify(self, text: str) -> TopicClassification:
        """
        Classify using regex patterns.
        
        Returns the topic with the most pattern matches.
        """
        scores: dict[str, int] = {}
        
        for topic, patterns in self.TOPIC_PATTERNS.items():
            count = 0
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    count += 1
            if count > 0:
                scores[topic] = count
        
        if not scores:
            return TopicClassification(
                topic="General",
                confidence=0.3,
                reasoning="No specific topic patterns matched"
            )
        
        # Get topic with highest score
        best_topic = max(scores, key=lambda k: scores[k])
        max_score = scores[best_topic]
        
        # Confidence based on number of matches
        confidence = min(0.5 + (max_score * 0.15), 0.95)
        
        return TopicClassification(
            topic=best_topic,
            confidence=confidence,
            reasoning=f"Matched {max_score} patterns for {best_topic}"
        )
    
    async def _ai_classify(
        self,
        title: str,
        abstract: Optional[str],
    ) -> Optional[TopicClassification]:
        """
        Use AI (Claude/AK) for more accurate classification.
        
        This is optional and used when pattern matching has low confidence.
        """
        # TODO: Integrate with AK MCP for AI classification
        # For now, return None to use pattern-based result
        logger.debug("AI classification not yet implemented, using pattern-based")
        return None
    
    async def classify_batch(
        self,
        papers: list[dict],
        use_ai: bool = False,
    ) -> list[TopicClassification]:
        """
        Classify multiple papers.
        
        Args:
            papers: List of dicts with 'title' and optional 'abstract' keys
            use_ai: Whether to use AI for classification
            
        Returns:
            List of TopicClassification results in same order as input
        """
        results = []
        for paper in papers:
            result = await self.classify(
                title=paper.get("title", ""),
                abstract=paper.get("abstract"),
                use_ai=use_ai,
            )
            results.append(result)
        return results


# Singleton instance
_classifier: Optional[TopicClassifierService] = None


def get_topic_classifier() -> TopicClassifierService:
    """Get or create the topic classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = TopicClassifierService()
    return _classifier

