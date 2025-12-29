'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuthStore, useProjectStore } from '@/lib/store';
import { api, PaperListItem, ClaimWithSources, SectionWithClaims, TreeNode } from '@/lib/api';

import { ExplorePanel } from '@/components/research/explore-panel';
import { OutlinePanel } from '@/components/research/outline-panel';
import { ChatPanel } from '@/components/research/chat-panel';
import { KnowledgeTreePanel } from '@/components/research/knowledge-tree-panel';
import { DetailsPanel } from '@/components/research/details-panel';

type SelectedItem =
  | { type: 'paper'; paper: PaperListItem }
  | { type: 'claim'; claim: ClaimWithSources; section: SectionWithClaims }
  | null;

export default function ResearchPage() {
  const params = useParams();
  const projectId = params.id as string;
  const token = useAuthStore((s) => s.token) || 'demo-token';
  const project = useProjectStore((s) => s.currentProject);

  const [selectedItem, setSelectedItem] = useState<SelectedItem>(null);
  const [activeTab, setActiveTab] = useState('explore');
  const [chatInput, setChatInput] = useState('');

  // Fetch session info
  const { data: session } = useQuery({
    queryKey: ['research-session', projectId],
    queryFn: () => api.getResearchSession(token, projectId),
  });

  // Handlers
  const handleSelectPaper = useCallback((paper: PaperListItem) => {
    setSelectedItem({ type: 'paper', paper });
  }, []);

  const handleSelectClaim = useCallback((claim: ClaimWithSources, section: SectionWithClaims) => {
    setSelectedItem({ type: 'claim', claim, section });
  }, []);

  const handleSelectTreeNode = useCallback((node: TreeNode) => {
    if (node.paper_index) {
      // This is a source node, find the paper
      // For now, create a minimal paper object from the node
      setSelectedItem({
        type: 'paper',
        paper: {
          index: node.paper_index,
          paper_id: node.id,
          node_id: node.id,
          source_id: null,
          title: node.title,
          authors: [],
          year: node.year,
          summary: '',
          citation_count: null,
          relevance_score: 0,
          user_rating: node.user_rating,
          is_ingested: true,
          pdf_url: null,
        },
      });
    }
  }, []);

  const handlePaperClick = useCallback((index: number) => {
    // Switch to explore tab and select the paper
    setActiveTab('explore');
    // The explore panel will handle the selection via query
  }, []);

  const handleCloseDetails = useCallback(() => {
    setSelectedItem(null);
  }, []);

  const handleChatInsert = useCallback((text: string) => {
    setChatInput((prev) => `${prev} ${text}`.trim());
  }, []);

  const selectedPaper = selectedItem?.type === 'paper' ? selectedItem.paper : null;

  return (
    <div className="page-transition flex h-[calc(100vh-4rem)] flex-col">
      {/* Header */}
      <div className="shrink-0 px-6 py-4 border-b">
        <h1 className="font-serif text-2xl font-bold">{project?.title || 'Research'}</h1>
        {session && (
          <p className="text-sm text-muted-foreground mt-1">
            Researching: {session.topic} • {session.papers_found} papers • {session.outline_sections} sections
          </p>
        )}
        {!session && (
          <p className="text-sm text-muted-foreground mt-1">
            Start by searching for papers in the chat
          </p>
        )}
      </div>

      {/* Main content: 2 columns */}
      <div className="flex flex-1 min-h-0">
        {/* Left: 3 Tabs */}
        <div className="w-1/2 flex flex-col border-r">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <TabsList className="w-full justify-start rounded-none border-b bg-transparent h-auto p-0">
              <TabsTrigger
                value="explore"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 py-2"
              >
                Explore
              </TabsTrigger>
              <TabsTrigger
                value="tree"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 py-2"
              >
                Knowledge Tree
              </TabsTrigger>
              <TabsTrigger
                value="outline"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 py-2"
              >
                Outline
              </TabsTrigger>
            </TabsList>

            <div className="flex-1 min-h-0 overflow-hidden">
              <TabsContent value="explore" className="h-full m-0 p-0">
                <ExplorePanel
                  projectId={projectId}
                  onSelectPaper={handleSelectPaper}
                  selectedPaperId={selectedPaper?.node_id}
                />
              </TabsContent>

              <TabsContent value="tree" className="h-full m-0 p-0">
                <KnowledgeTreePanel
                  projectId={projectId}
                  onSelectNode={handleSelectTreeNode}
                  selectedNodeId={selectedPaper?.node_id}
                />
              </TabsContent>

              <TabsContent value="outline" className="h-full m-0 p-0">
                <OutlinePanel
                  projectId={projectId}
                  onSelectClaim={handleSelectClaim}
                  onPaperClick={handlePaperClick}
                />
              </TabsContent>
            </div>
          </Tabs>

          {/* Details panel at bottom */}
          {selectedItem && (
            <DetailsPanel
              projectId={projectId}
              selectedItem={selectedItem}
              onClose={handleCloseDetails}
              onChatInsert={handleChatInsert}
            />
          )}
        </div>

        {/* Right: Always-visible chat */}
        <div className="w-1/2 flex flex-col">
          <ChatPanel
            projectId={projectId}
            selectedPaper={selectedPaper}
            onPaperMention={handlePaperClick}
          />
        </div>
      </div>
    </div>
  );
}
