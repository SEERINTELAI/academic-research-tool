"""
Unit tests for TopicClassifierService.
"""

import pytest
from src.services.topic_classifier import TopicClassifierService, TopicClassification


class TestTopicClassifier:
    """Tests for topic classification."""
    
    @pytest.fixture
    def classifier(self) -> TopicClassifierService:
        """Create a classifier instance."""
        return TopicClassifierService()
    
    @pytest.mark.asyncio
    async def test_classify_machine_learning(self, classifier: TopicClassifierService):
        """Test classification of ML paper."""
        result = await classifier.classify(
            title="Deep Learning for Natural Language Processing",
            abstract="We present a neural network approach using transformers..."
        )
        
        assert result.topic in ["Machine Learning", "Natural Language Processing"]
        assert result.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_classify_quantum_computing(self, classifier: TopicClassifierService):
        """Test classification of quantum paper."""
        result = await classifier.classify(
            title="Quantum Circuit Optimization for NISQ Devices",
            abstract="We develop algorithms for noisy intermediate-scale quantum computers..."
        )
        
        assert result.topic == "Quantum Computing"
        assert result.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_classify_cryptography(self, classifier: TopicClassifierService):
        """Test classification of security paper."""
        result = await classifier.classify(
            title="Post-Quantum Cryptographic Schemes Based on Lattices",
            abstract="We analyze the security of lattice-based encryption against quantum attacks..."
        )
        
        assert result.topic == "Cryptography & Security"
        assert result.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_classify_general(self, classifier: TopicClassifierService):
        """Test classification of paper with no clear topic."""
        result = await classifier.classify(
            title="A Study of Something Very Generic",
            abstract="This paper studies something."
        )
        
        # Should default to "General" with low confidence
        assert result.topic == "General"
        assert result.confidence < 0.5
    
    @pytest.mark.asyncio
    async def test_classify_without_abstract(self, classifier: TopicClassifierService):
        """Test classification with title only."""
        result = await classifier.classify(
            title="Reinforcement Learning in Robotics Applications",
        )
        
        # Should still work with title alone
        assert result.topic in ["Machine Learning", "Robotics & Control"]
        assert result.confidence > 0.3
    
    @pytest.mark.asyncio
    async def test_classify_batch(self, classifier: TopicClassifierService):
        """Test batch classification."""
        papers = [
            {"title": "Deep Learning for Image Recognition", "abstract": "CNN-based approach..."},
            {"title": "Blockchain Security Analysis", "abstract": "We study vulnerabilities..."},
            {"title": "RNA Sequence Analysis", "abstract": "Bioinformatics approach..."},
        ]
        
        results = await classifier.classify_batch(papers)
        
        assert len(results) == 3
        assert results[0].topic in ["Machine Learning", "Computer Vision"]
        assert results[1].topic == "Cryptography & Security"
        assert results[2].topic == "Bioinformatics"
    
    @pytest.mark.asyncio
    async def test_pattern_matching_multiple_topics(self, classifier: TopicClassifierService):
        """Test that papers matching multiple topics pick the best one."""
        result = await classifier.classify(
            title="Machine Learning for Quantum Computing Optimization",
            abstract="We apply neural networks to optimize quantum circuits..."
        )
        
        # Should pick one topic, not multiple
        assert result.topic in ["Machine Learning", "Quantum Computing"]
        assert result.confidence > 0.5

