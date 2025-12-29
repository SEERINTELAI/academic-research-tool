'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Network, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { api, TreeNode, KnowledgeTreeGraph } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

interface KnowledgeTreePanelProps {
  projectId: string;
  onSelectNode?: (node: TreeNode) => void;
  selectedNodeId?: string;
}

// Simple force-directed layout (no external library needed)
interface LayoutNode extends TreeNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

function forceLayout(
  nodes: TreeNode[],
  edges: { source: string; target: string }[],
  width: number,
  height: number
): LayoutNode[] {
  if (nodes.length === 0) return [];

  // Initialize positions randomly
  const layoutNodes: LayoutNode[] = nodes.map((node) => ({
    ...node,
    x: Math.random() * width,
    y: Math.random() * height,
    vx: 0,
    vy: 0,
  }));

  const nodeMap = new Map<string, LayoutNode>();
  layoutNodes.forEach((n) => nodeMap.set(n.id, n));

  // Run simulation for a few iterations
  const iterations = 100;
  const repulsion = 5000;
  const attraction = 0.01;
  const damping = 0.8;

  for (let i = 0; i < iterations; i++) {
    // Repulsion between all nodes
    for (let a = 0; a < layoutNodes.length; a++) {
      for (let b = a + 1; b < layoutNodes.length; b++) {
        const nodeA = layoutNodes[a];
        const nodeB = layoutNodes[b];
        const dx = nodeA.x - nodeB.x;
        const dy = nodeA.y - nodeB.y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const force = repulsion / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        nodeA.vx += fx;
        nodeA.vy += fy;
        nodeB.vx -= fx;
        nodeB.vy -= fy;
      }
    }

    // Attraction along edges
    edges.forEach((edge) => {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (source && target) {
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const fx = dx * attraction;
        const fy = dy * attraction;
        source.vx += fx;
        source.vy += fy;
        target.vx -= fx;
        target.vy -= fy;
      }
    });

    // Center gravity
    const centerX = width / 2;
    const centerY = height / 2;
    layoutNodes.forEach((node) => {
      node.vx += (centerX - node.x) * 0.001;
      node.vy += (centerY - node.y) * 0.001;
    });

    // Apply velocities with damping
    layoutNodes.forEach((node) => {
      node.vx *= damping;
      node.vy *= damping;
      node.x += node.vx;
      node.y += node.vy;
      // Keep in bounds
      node.x = Math.max(50, Math.min(width - 50, node.x));
      node.y = Math.max(50, Math.min(height - 50, node.y));
    });
  }

  return layoutNodes;
}

function GraphCanvas({
  graph,
  onSelectNode,
  selectedNodeId,
}: {
  graph: KnowledgeTreeGraph;
  onSelectNode?: (node: TreeNode) => void;
  selectedNodeId?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [layoutNodes, setLayoutNodes] = useState<LayoutNode[]>([]);
  const [scale, setScale] = useState(1);
  const [hoveredNode, setHoveredNode] = useState<LayoutNode | null>(null);

  // Calculate layout when graph changes
  useEffect(() => {
    if (graph.nodes.length > 0 && containerRef.current) {
      const width = containerRef.current.clientWidth;
      const height = containerRef.current.clientHeight;
      const nodes = forceLayout(graph.nodes, graph.edges, width, height);
      setLayoutNodes(nodes);
    }
  }, [graph]);

  // Draw canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || layoutNodes.length === 0) return;

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);
    ctx.save();

    // Apply zoom
    const centerX = width / 2;
    const centerY = height / 2;
    ctx.translate(centerX, centerY);
    ctx.scale(scale, scale);
    ctx.translate(-centerX, -centerY);

    const nodeMap = new Map<string, LayoutNode>();
    layoutNodes.forEach((n) => nodeMap.set(n.id, n));

    // Draw edges with arrows (source cites target)
    ctx.strokeStyle = 'rgba(100, 100, 100, 0.4)';
    ctx.fillStyle = 'rgba(100, 100, 100, 0.4)';
    ctx.lineWidth = 1.5;
    
    graph.edges.forEach((edge) => {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (source && target) {
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const len = Math.sqrt(dx * dx + dy * dy);
        if (len === 0) return;
        
        // Normalize direction
        const nx = dx / len;
        const ny = dy / len;
        
        // Calculate arrow endpoint (stop at node edge)
        const sourceRadius = source.size || 10;
        const targetRadius = target.size || 10;
        const startX = source.x + nx * sourceRadius;
        const startY = source.y + ny * sourceRadius;
        const endX = target.x - nx * (targetRadius + 6);
        const endY = target.y - ny * (targetRadius + 6);
        
        // Draw line
        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.lineTo(endX, endY);
        ctx.stroke();
        
        // Draw arrowhead
        const arrowSize = 5;
        const angle = Math.atan2(dy, dx);
        ctx.beginPath();
        ctx.moveTo(endX, endY);
        ctx.lineTo(
          endX - arrowSize * Math.cos(angle - Math.PI / 6),
          endY - arrowSize * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
          endX - arrowSize * Math.cos(angle + Math.PI / 6),
          endY - arrowSize * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fill();
      }
    });

    // Draw nodes
    layoutNodes.forEach((node) => {
      const isSelected = node.id === selectedNodeId;
      const isHovered = node.id === hoveredNode?.id;
      const radius = (node.size || 10) * (isSelected ? 1.3 : 1) * (isHovered ? 1.2 : 1);

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = node.color || '#6B7280';
      ctx.fill();

      // Selected/hovered ring
      if (isSelected || isHovered) {
        ctx.strokeStyle = isSelected ? '#3B82F6' : 'rgba(59, 130, 246, 0.5)';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Label
      ctx.fillStyle = '#374151';
      ctx.font = '10px system-ui, sans-serif';
      ctx.textAlign = 'center';
      const label = node.paper_index ? `#${node.paper_index}` : node.label.slice(0, 15);
      ctx.fillText(label, node.x, node.y + radius + 12);
    });

    ctx.restore();
  }, [layoutNodes, scale, selectedNodeId, hoveredNode, graph.edges]);

  // Handle mouse events
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    // Find hovered node
    let found: LayoutNode | null = null;
    for (const node of layoutNodes) {
      const dx = node.x - x;
      const dy = node.y - y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < (node.size || 10) * 1.5) {
        found = node;
        break;
      }
    }
    setHoveredNode(found);
  }, [layoutNodes, scale]);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (hoveredNode && onSelectNode) {
      onSelectNode(hoveredNode);
    }
  }, [hoveredNode, onSelectNode]);

  return (
    <div ref={containerRef} className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-pointer"
        onMouseMove={handleMouseMove}
        onClick={handleClick}
        style={{ cursor: hoveredNode ? 'pointer' : 'default' }}
      />

      {/* Zoom controls */}
      <div className="absolute bottom-4 right-4 flex gap-1">
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => setScale((s) => Math.min(2, s + 0.2))}
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => setScale(1)}
        >
          <Maximize2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Tooltip */}
      {hoveredNode && (
        <div
          className="absolute bg-popover border rounded-lg shadow-lg p-2 text-xs max-w-[250px] pointer-events-none z-50"
          style={{
            left: Math.min(hoveredNode.x * scale + 20, containerRef.current?.clientWidth ?? 400 - 260),
            top: Math.max(hoveredNode.y * scale - 10, 10),
          }}
        >
          <p className="font-medium line-clamp-3">{hoveredNode.title}</p>
          {hoveredNode.year && (
            <p className="text-muted-foreground mt-1">Published: {hoveredNode.year}</p>
          )}
          {hoveredNode.paper_index && (
            <Badge variant="secondary" className="mt-1 text-[10px]">
              #{hoveredNode.paper_index} in library
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <Skeleton className="h-32 w-32 rounded-full mx-auto mb-4" />
        <Skeleton className="h-4 w-24 mx-auto" />
      </div>
    </div>
  );
}

export function KnowledgeTreePanel({
  projectId,
  onSelectNode,
  selectedNodeId,
}: KnowledgeTreePanelProps) {
  const token = useAuthStore((s) => s.token) || 'demo-token';

  const { data: graph, isLoading, error } = useQuery({
    queryKey: ['knowledge-tree', projectId],
    queryFn: () => api.getKnowledgeTree(token, projectId),
  });

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <Network className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="font-medium mb-2">Error loading tree</h3>
        <p className="text-sm text-muted-foreground">
          {error instanceof Error ? error.message : 'Something went wrong'}
        </p>
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <Network className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="font-medium mb-2">No papers in library yet</h3>
        <p className="text-sm text-muted-foreground">
          Ingest papers to see their citation relationships.
          <br />
          <span className="text-xs text-muted-foreground/70">
            The tree shows how library papers cite each other.
          </span>
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Stats header */}
      <div className="shrink-0 px-4 py-2 border-b flex items-center gap-4 text-xs text-muted-foreground">
        <span>{graph.total_papers} library papers</span>
        <span>•</span>
        <span>{graph.edges.length} citations</span>
      </div>

      {/* Graph */}
      <div className="flex-1 min-h-0">
        <GraphCanvas
          graph={graph}
          onSelectNode={onSelectNode}
          selectedNodeId={selectedNodeId}
        />
      </div>

      {/* Legend */}
      <div className="shrink-0 px-4 py-2 border-t flex items-center gap-4 text-[10px]">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#10B981]" />
          Library Paper
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-[1px] bg-gray-400" />
          Cites
        </span>
        <span className="text-muted-foreground">
          Node size = citation count
        </span>
      </div>
    </div>
  );
}

