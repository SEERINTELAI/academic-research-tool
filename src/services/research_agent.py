"""
AI Research Agent Service.

Orchestrates the research process:
1. Explores topics by searching academic databases
2. Auto-ingests relevant papers into RAG
3. Builds a knowledge tree of findings
4. Generates outline from accumulated knowledge
5. Handles user critiques and refinement
"""

import logging
from typing import Optional
from uuid import UUID, uuid4

from src.config import get_settings
from src.models.knowledge import (
    CritiqueRequest,
    DeepenRequest,
    EvidenceStrength,
    ExploreRequest,
    ExploreResult,
    GenerateOutlineRequest,
    GenerateOutlineResult,
    KnowledgeNode,
    KnowledgeNodeCreate,
    KnowledgeTree,
    NodeType,
    OutlineClaim,
    OutlineClaimCreate,
    ResearchSession,
    ResearchSessionCreate,
    SessionStatus,
)
from src.services.ak_client import AKClient
from src.services.database import get_supabase_client
from src.services.hyperion_client import HyperionClient
from src.services.semantic_scholar import SemanticScholarClient

logger = logging.getLogger(__name__)


class ResearchAgentError(Exception):
    """Research agent error."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ResearchAgent:
    """
    AI-powered research agent.
    
    Manages the research workflow:
    - Topic exploration
    - Paper discovery and ingestion
    - Knowledge tree building
    - Outline generation
    - User feedback handling
    
    Usage:
        agent = ResearchAgent(project_id)
        session = await agent.start_session("quantum cryptography")
        result = await agent.explore()
        outline = await agent.generate_outline()
    """
    
    def __init__(self, project_id: UUID, session_id: Optional[UUID] = None):
        """
        Initialize research agent.
        
        Args:
            project_id: Project to research for.
            session_id: Existing session to continue (optional).
        """
        self.project_id = project_id
        self.session_id = session_id
        self.db = get_supabase_client()
        self.settings = get_settings()
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    async def start_session(self, topic: str, guidance: Optional[str] = None) -> ResearchSession:
        """
        Start a new research session.
        
        Args:
            topic: Research topic.
            guidance: Optional user guidance for AI direction.
        
        Returns:
            New research session.
        """
        result = self.db.table("research_session").insert({
            "project_id": str(self.project_id),
            "topic": topic,
            "status": SessionStatus.EXPLORING.value,
            "guidance_notes": guidance,
        }).execute()
        
        if not result.data:
            raise ResearchAgentError("Failed to create research session")
        
        session = ResearchSession(**result.data[0])
        self.session_id = session.id
        
        # Log the action
        await self._log_action(
            action_type="search",
            trigger="user_request",
            description=f"Started research session on: {topic}",
            user_input=guidance,
        )
        
        logger.info(f"Started research session {session.id} on: {topic}")
        return session
    
    async def get_session(self) -> Optional[ResearchSession]:
        """Get current session."""
        if not self.session_id:
            # Try to get the latest session for the project
            result = self.db.table("research_session")\
                .select("*")\
                .eq("project_id", str(self.project_id))\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                session = ResearchSession(**result.data[0])
                self.session_id = session.id
                return session
            return None
        
        result = self.db.table("research_session")\
            .select("*")\
            .eq("id", str(self.session_id))\
            .execute()
        
        if result.data:
            return ResearchSession(**result.data[0])
        return None
    
    # ========================================================================
    # Exploration
    # ========================================================================
    
    async def explore(self, request: ExploreRequest) -> ExploreResult:
        """
        Explore a topic - search, filter, and ingest papers.
        
        Args:
            request: Exploration parameters.
        
        Returns:
            Exploration results.
        """
        session = await self.get_session()
        if not session:
            raise ResearchAgentError("No active research session")
        
        topic = request.topic or session.topic
        
        # 1. Search for papers
        logger.info(f"Searching for papers on: {topic}")
        async with SemanticScholarClient() as scholar:
            search_result = await scholar.search(
                query=topic,
                limit=request.max_papers * 2,  # Get extra to filter
            )
        
        papers = search_result.results
        logger.info(f"Found {len(papers)} papers")
        
        if not papers:
            return ExploreResult(
                papers_found=0,
                papers_ingested=0,
                nodes_created=0,
                summaries=[],
                suggested_subtopics=[],
                exploration_log_id=uuid4(),
            )
        
        # 2. Filter by relevance (use AI via AK)
        relevant_papers = await self._filter_relevant_papers(
            papers, topic, request.guidance
        )
        logger.info(f"Filtered to {len(relevant_papers)} relevant papers")
        
        # 3. Create source records and ingest
        ingested_count = 0
        nodes_created = 0
        
        for paper in relevant_papers[:request.max_papers]:
            try:
                # Create source in database
                source_id = await self._create_source(paper)
                
                # Ingest into RAG if auto_ingest enabled
                if request.auto_ingest and paper.get("pdf_url"):
                    await self._ingest_paper(source_id, paper)
                    ingested_count += 1
                
                # Create knowledge node
                node = await self._create_knowledge_node(
                    node_type=NodeType.SOURCE,
                    title=paper.get("title", "Unknown"),
                    content=paper.get("abstract", ""),
                    source_id=source_id,
                    confidence=paper.get("relevance_score", 0.7),
                )
                nodes_created += 1
                
            except Exception as e:
                logger.warning(f"Failed to process paper: {e}")
                continue
        
        # 4. Generate summaries of findings
        summaries = await self._generate_summaries(relevant_papers[:request.max_papers])
        
        # 5. Identify subtopics for deeper exploration
        subtopics = await self._identify_subtopics(relevant_papers[:request.max_papers], topic)
        
        # Log the action
        log_id = await self._log_action(
            action_type="search",
            trigger="auto" if not request.guidance else "user_request",
            description=f"Explored topic: {topic}",
            user_input=request.guidance,
            details={
                "papers_found": len(papers),
                "papers_ingested": ingested_count,
                "subtopics": subtopics,
            },
            nodes_created=nodes_created,
            sources_ingested=ingested_count,
        )
        
        return ExploreResult(
            papers_found=len(papers),
            papers_ingested=ingested_count,
            nodes_created=nodes_created,
            summaries=summaries,
            suggested_subtopics=subtopics,
            exploration_log_id=log_id,
        )
    
    async def deepen(self, request: DeepenRequest) -> ExploreResult:
        """
        Go deeper on a specific subtopic.
        
        Args:
            request: Deepen request with subtopic.
        
        Returns:
            Exploration results.
        """
        session = await self.get_session()
        if not session:
            raise ResearchAgentError("No active research session")
        
        # Create a topic node as parent
        parent_id = request.parent_node_id
        if not parent_id:
            topic_node = await self._create_knowledge_node(
                node_type=NodeType.TOPIC,
                title=request.subtopic,
                content=f"Deeper exploration of: {request.subtopic}",
            )
            parent_id = topic_node.id
        
        # Explore the subtopic
        explore_request = ExploreRequest(
            topic=f"{session.topic} {request.subtopic}",
            guidance=request.guidance,
            max_papers=request.max_papers,
            auto_ingest=True,
        )
        
        result = await self.explore(explore_request)
        
        # Update nodes to have the parent
        if parent_id:
            # This would update the created nodes - simplified for now
            pass
        
        return result
    
    # ========================================================================
    # Knowledge Tree
    # ========================================================================
    
    async def get_knowledge_tree(self) -> KnowledgeTree:
        """
        Get the full knowledge tree for the current session.
        
        Returns:
            Knowledge tree with all nodes.
        """
        session = await self.get_session()
        if not session:
            raise ResearchAgentError("No active research session")
        
        result = self.db.table("knowledge_node")\
            .select("*")\
            .eq("session_id", str(self.session_id))\
            .eq("is_hidden", False)\
            .order("order_index")\
            .execute()
        
        nodes = [KnowledgeNode(**row) for row in result.data]
        
        # Build tree structure
        tree_nodes = self._build_tree(nodes)
        
        # Count sources
        source_count = len([n for n in nodes if n.source_id])
        
        return KnowledgeTree(
            session_id=self.session_id,
            topic=session.topic,
            nodes=tree_nodes,
            total_nodes=len(nodes),
            total_sources=source_count,
        )
    
    async def rate_node(
        self,
        node_id: UUID,
        rating: str,
        note: Optional[str] = None,
    ) -> KnowledgeNode:
        """
        Rate a knowledge node.
        
        Args:
            node_id: Node to rate.
            rating: "useful", "neutral", or "irrelevant".
            note: Optional user note.
        
        Returns:
            Updated node.
        """
        result = self.db.table("knowledge_node")\
            .update({
                "user_rating": rating,
                "user_note": note,
                "is_hidden": rating == "irrelevant",
            })\
            .eq("id", str(node_id))\
            .execute()
        
        if not result.data:
            raise ResearchAgentError("Node not found")
        
        return KnowledgeNode(**result.data[0])
    
    async def suggest_direction(self, suggestion: str) -> ExploreResult:
        """
        Handle user suggestion for research direction.
        
        Args:
            suggestion: User's suggested direction.
        
        Returns:
            Exploration results.
        """
        return await self.explore(ExploreRequest(
            topic=suggestion,
            guidance=f"User suggested exploring: {suggestion}",
            max_papers=5,
            auto_ingest=True,
        ))
    
    # ========================================================================
    # Outline Generation
    # ========================================================================
    
    async def generate_outline(
        self,
        request: Optional[GenerateOutlineRequest] = None,
    ) -> GenerateOutlineResult:
        """
        Generate an outline from the knowledge tree.
        
        Args:
            request: Generation parameters.
        
        Returns:
            Generation results.
        """
        if request is None:
            request = GenerateOutlineRequest()
        
        session = await self.get_session()
        if not session:
            raise ResearchAgentError("No active research session")
        
        # Get knowledge tree
        tree = await self.get_knowledge_tree()
        
        if tree.total_nodes == 0:
            raise ResearchAgentError("No knowledge nodes to generate outline from")
        
        # Use AI to cluster and structure
        outline_structure = await self._generate_outline_structure(
            tree.nodes, 
            session.topic,
            request.max_sections,
        )
        
        # Create outline sections and claims
        sections_created = 0
        claims_created = 0
        
        for section_data in outline_structure:
            section_id = await self._create_outline_section(
                title=section_data["title"],
                section_type=section_data.get("type", "heading"),
                order_index=sections_created,
            )
            sections_created += 1
            
            # Create claims for this section
            for claim_data in section_data.get("claims", []):
                await self._create_outline_claim(
                    section_id=section_id,
                    claim_text=claim_data["text"],
                    supporting_nodes=claim_data.get("supporting_nodes", []),
                    order_index=claims_created,
                )
                claims_created += 1
        
        # Update session status
        self.db.table("research_session")\
            .update({"status": SessionStatus.DRAFTING.value})\
            .eq("id", str(self.session_id))\
            .execute()
        
        # Log the action
        await self._log_action(
            action_type="generate_outline",
            trigger="user_request",
            description=f"Generated outline with {sections_created} sections",
            details={
                "sections_created": sections_created,
                "claims_created": claims_created,
            },
        )
        
        return GenerateOutlineResult(
            sections_created=sections_created,
            claims_created=claims_created,
            outline_summary=f"Created {sections_created} sections with {claims_created} claims",
        )
    
    # ========================================================================
    # Critique Handling
    # ========================================================================
    
    async def handle_critique(
        self,
        claim_id: UUID,
        critique: CritiqueRequest,
    ) -> dict:
        """
        Handle user critique of a claim.
        
        Args:
            claim_id: Claim being critiqued.
            critique: Critique details.
        
        Returns:
            Action taken result.
        """
        # Get the claim
        result = self.db.table("outline_claim")\
            .select("*")\
            .eq("id", str(claim_id))\
            .execute()
        
        if not result.data:
            raise ResearchAgentError("Claim not found")
        
        claim = OutlineClaim(**result.data[0])
        
        if critique.critique_type == "needs_more_sources":
            # Search for more papers supporting this claim
            explore_result = await self.explore(ExploreRequest(
                topic=claim.claim_text,
                guidance=f"Find papers that support or discuss: {claim.claim_text}",
                max_papers=5,
                auto_ingest=True,
            ))
            
            # Update claim with new sources
            # ... (simplified)
            
            return {
                "action": "found_more_sources",
                "papers_found": explore_result.papers_found,
                "papers_ingested": explore_result.papers_ingested,
            }
        
        elif critique.critique_type == "irrelevant":
            # Mark claim as rejected
            self.db.table("outline_claim")\
                .update({
                    "status": "rejected",
                    "user_critique": critique.details or "Marked as irrelevant",
                })\
                .eq("id", str(claim_id))\
                .execute()
            
            return {"action": "claim_rejected"}
        
        elif critique.critique_type == "expand":
            # Generate sub-claims or deeper exploration
            explore_result = await self.deepen(DeepenRequest(
                subtopic=claim.claim_text,
                guidance=critique.details,
                max_papers=5,
            ))
            
            return {
                "action": "expanded",
                "new_nodes": explore_result.nodes_created,
            }
        
        return {"action": "unknown_critique_type"}
    
    # ========================================================================
    # Private Helpers
    # ========================================================================
    
    async def _filter_relevant_papers(
        self,
        papers: list[dict],
        topic: str,
        guidance: Optional[str],
    ) -> list[dict]:
        """Use AI to filter papers by relevance."""
        # For now, simple filtering by title/abstract match
        # TODO: Use AK for smarter filtering
        
        scored = []
        topic_words = set(topic.lower().split())
        
        for paper in papers:
            title = (paper.get("title") or "").lower()
            abstract = (paper.get("abstract") or "").lower()
            text = f"{title} {abstract}"
            
            # Simple relevance scoring
            matches = sum(1 for w in topic_words if w in text)
            score = matches / len(topic_words) if topic_words else 0
            
            # Boost for citation count
            citations = paper.get("citation_count") or 0
            if citations > 100:
                score += 0.2
            elif citations > 20:
                score += 0.1
            
            paper["relevance_score"] = min(score, 1.0)
            scored.append(paper)
        
        # Sort by relevance
        scored.sort(key=lambda p: p["relevance_score"], reverse=True)
        
        # Return papers with relevance > 0.3
        return [p for p in scored if p["relevance_score"] > 0.3]
    
    async def _create_source(self, paper: dict) -> UUID:
        """Create a source record from a paper."""
        result = self.db.table("source").insert({
            "project_id": str(self.project_id),
            "paper_id": paper.get("paper_id"),
            "title": paper.get("title", "Unknown"),
            "authors": paper.get("authors", []),
            "abstract": paper.get("abstract"),
            "publication_year": paper.get("year"),
            "doi": paper.get("doi"),
            "pdf_url": paper.get("pdf_url"),
            "ingestion_status": "pending",
        }).execute()
        
        if not result.data:
            raise ResearchAgentError("Failed to create source")
        
        return UUID(result.data[0]["id"])
    
    async def _ingest_paper(self, source_id: UUID, paper: dict) -> None:
        """Ingest a paper into RAG."""
        try:
            async with HyperionClient() as hyperion:
                # Download and upload PDF
                pdf_url = paper.get("pdf_url")
                if pdf_url:
                    from src.services.pdf_processor import PDFDownloader
                    downloader = PDFDownloader()
                    pdf_bytes, filename = await downloader.download(pdf_url)
                    
                    if pdf_bytes:
                        await hyperion.upload_pdf(pdf_bytes, filename)
                        
                        # Update source status
                        self.db.table("source")\
                            .update({"ingestion_status": "ready"})\
                            .eq("id", str(source_id))\
                            .execute()
        except Exception as e:
            logger.warning(f"Failed to ingest paper: {e}")
    
    async def _create_knowledge_node(
        self,
        node_type: NodeType,
        title: str,
        content: Optional[str] = None,
        source_id: Optional[UUID] = None,
        parent_id: Optional[UUID] = None,
        confidence: float = 0.5,
    ) -> KnowledgeNode:
        """Create a knowledge node."""
        result = self.db.table("knowledge_node").insert({
            "session_id": str(self.session_id),
            "source_id": str(source_id) if source_id else None,
            "parent_node_id": str(parent_id) if parent_id else None,
            "node_type": node_type.value,
            "title": title,
            "content": content,
            "confidence": confidence,
        }).execute()
        
        if not result.data:
            raise ResearchAgentError("Failed to create knowledge node")
        
        return KnowledgeNode(**result.data[0])
    
    async def _generate_summaries(self, papers: list[dict]) -> list[str]:
        """Generate summaries of papers."""
        # For now, use abstracts as summaries
        # TODO: Use AK for smarter summarization
        summaries = []
        for paper in papers[:5]:
            abstract = paper.get("abstract", "")
            if abstract:
                # Truncate to first 200 chars
                summary = abstract[:200] + "..." if len(abstract) > 200 else abstract
                summaries.append(f"**{paper.get('title', 'Unknown')}**: {summary}")
        return summaries
    
    async def _identify_subtopics(
        self,
        papers: list[dict],
        main_topic: str,
    ) -> list[str]:
        """Identify subtopics from papers."""
        # Simple keyword extraction - TODO: use AI
        word_freq: dict[str, int] = {}
        main_words = set(main_topic.lower().split())
        
        for paper in papers:
            title = (paper.get("title") or "").lower()
            for word in title.split():
                if len(word) > 4 and word not in main_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        # Top subtopics
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:5]]
    
    async def _generate_outline_structure(
        self,
        nodes: list[KnowledgeNode],
        topic: str,
        max_sections: int,
    ) -> list[dict]:
        """Generate outline structure from nodes."""
        # Simple structure - TODO: use AI for clustering
        
        # Group nodes by type
        sources = [n for n in nodes if n.node_type == NodeType.SOURCE]
        topics = [n for n in nodes if n.node_type == NodeType.TOPIC]
        
        outline = [
            {
                "title": "Introduction",
                "type": "introduction",
                "claims": [
                    {
                        "text": f"Overview of {topic}",
                        "supporting_nodes": [],
                    }
                ],
            },
        ]
        
        # Add sections for each topic node
        for topic_node in topics[:max_sections - 2]:
            section = {
                "title": topic_node.title,
                "type": "heading",
                "claims": [],
            }
            
            # Find sources under this topic
            child_sources = [n for n in sources if n.parent_node_id == topic_node.id]
            for source in child_sources[:3]:
                section["claims"].append({
                    "text": source.title,
                    "supporting_nodes": [str(source.id)],
                })
            
            outline.append(section)
        
        # Add conclusion
        outline.append({
            "title": "Conclusion",
            "type": "conclusion",
            "claims": [
                {
                    "text": f"Summary and future directions for {topic}",
                    "supporting_nodes": [],
                }
            ],
        })
        
        return outline
    
    async def _create_outline_section(
        self,
        title: str,
        section_type: str,
        order_index: int,
    ) -> UUID:
        """Create an outline section."""
        result = self.db.table("outline_section").insert({
            "project_id": str(self.project_id),
            "title": title,
            "section_type": section_type,
            "order_index": order_index,
        }).execute()
        
        if not result.data:
            raise ResearchAgentError("Failed to create outline section")
        
        return UUID(result.data[0]["id"])
    
    async def _create_outline_claim(
        self,
        section_id: UUID,
        claim_text: str,
        supporting_nodes: list,
        order_index: int,
    ) -> UUID:
        """Create an outline claim."""
        result = self.db.table("outline_claim").insert({
            "section_id": str(section_id),
            "claim_text": claim_text,
            "supporting_nodes": [str(n) for n in supporting_nodes],
            "order_index": order_index,
        }).execute()
        
        if not result.data:
            raise ResearchAgentError("Failed to create outline claim")
        
        return UUID(result.data[0]["id"])
    
    def _build_tree(self, nodes: list[KnowledgeNode]) -> list[KnowledgeNode]:
        """Build tree structure from flat list."""
        node_map = {n.id: n for n in nodes}
        roots = []
        
        for node in nodes:
            if node.parent_node_id and node.parent_node_id in node_map:
                parent = node_map[node.parent_node_id]
                parent.children.append(node)
            else:
                roots.append(node)
        
        return roots
    
    async def _log_action(
        self,
        action_type: str,
        trigger: str,
        description: str,
        user_input: Optional[str] = None,
        details: Optional[dict] = None,
        nodes_created: int = 0,
        sources_ingested: int = 0,
    ) -> UUID:
        """Log an exploration action."""
        result = self.db.table("exploration_log").insert({
            "session_id": str(self.session_id),
            "action_type": action_type,
            "trigger": trigger,
            "description": description,
            "user_input": user_input,
            "details": details,
            "nodes_created": nodes_created,
            "sources_ingested": sources_ingested,
        }).execute()
        
        if result.data:
            return UUID(result.data[0]["id"])
        return uuid4()

