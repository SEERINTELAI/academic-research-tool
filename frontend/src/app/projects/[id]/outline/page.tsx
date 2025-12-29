'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChevronRight,
  ChevronDown,
  Plus,
  GripVertical,
  Trash2,
  FileText,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, OutlineSection, OutlineSectionCreate } from '@/lib/api';
import { useAuthStore, useOutlineStore, useProjectStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const sectionTypes = [
  'heading',
  'abstract',
  'introduction',
  'methods',
  'results',
  'discussion',
  'conclusion',
  'references',
] as const;

function SectionItem({
  section,
  depth = 0,
  onAddChild,
  onDelete,
}: {
  section: OutlineSection;
  depth?: number;
  onAddChild: (parentId: string) => void;
  onDelete: (id: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = section.children && section.children.length > 0;

  return (
    <div className="group">
      <div
        className="flex items-center gap-2 rounded-lg border border-transparent px-2 py-2 transition-colors hover:border-border hover:bg-muted/50"
        style={{ paddingLeft: `${depth * 24 + 8}px` }}
      >
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex h-5 w-5 items-center justify-center text-muted-foreground"
          disabled={!hasChildren}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )
          ) : (
            <span className="h-4 w-4" />
          )}
        </button>
        
        <GripVertical className="h-4 w-4 cursor-grab text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        
        <FileText className="h-4 w-4 text-primary" />
        
        <span className="flex-1 font-medium">{section.title}</span>
        
        <Badge variant="secondary" className="text-xs">
          {section.section_type}
        </Badge>
        
        {section.research_questions?.length > 0 && (
          <Badge variant="outline" className="text-xs">
            {section.research_questions.length} questions
          </Badge>
        )}
        
        <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => onAddChild(section.id)}
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive hover:text-destructive"
            onClick={() => onDelete(section.id)}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      
      {isExpanded && hasChildren && (
        <div>
          {section.children!.map((child) => (
            <SectionItem
              key={child.id}
              section={child}
              depth={depth + 1}
              onAddChild={onAddChild}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function OutlinePage() {
  const params = useParams();
  const projectId = params.id as string;
  const queryClient = useQueryClient();
  
  const token = useAuthStore((s) => s.token);
  const project = useProjectStore((s) => s.currentProject);
  const sections = useOutlineStore((s) => s.sections);
  
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newSectionTitle, setNewSectionTitle] = useState('');
  const [newSectionType, setNewSectionType] = useState<string>('heading');
  const [parentId, setParentId] = useState<string | null>(null);

  const authToken = token || 'demo-token';

  const createMutation = useMutation({
    mutationFn: (data: OutlineSectionCreate) =>
      api.createOutlineSection(authToken, projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outline', projectId] });
      toast.success('Section added');
      setIsAddDialogOpen(false);
      setNewSectionTitle('');
      setNewSectionType('heading');
      setParentId(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add section');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (sectionId: string) =>
      api.deleteOutlineSection(authToken, projectId, sectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outline', projectId] });
      toast.success('Section deleted');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete section');
    },
  });

  const handleAddSection = () => {
    if (!newSectionTitle.trim()) {
      toast.error('Please enter a section title');
      return;
    }
    createMutation.mutate({
      title: newSectionTitle,
      section_type: newSectionType,
      parent_id: parentId,
    });
  };

  const openAddDialog = (parentSectionId: string | null = null) => {
    setParentId(parentSectionId);
    setIsAddDialogOpen(true);
  };

  // Build tree structure from flat sections
  const buildTree = (flatSections: OutlineSection[]): OutlineSection[] => {
    const map = new Map<string, OutlineSection>();
    const roots: OutlineSection[] = [];

    flatSections.forEach((s) => {
      map.set(s.id, { ...s, children: [] });
    });

    flatSections.forEach((s) => {
      const section = map.get(s.id)!;
      if (s.parent_id && map.has(s.parent_id)) {
        map.get(s.parent_id)!.children!.push(section);
      } else {
        roots.push(section);
      }
    });

    return roots.sort((a, b) => a.order_index - b.order_index);
  };

  const tree = buildTree(sections);

  return (
    <div className="page-transition p-6">
      <div className="mb-6">
        <h1 className="font-serif text-3xl font-bold">{project?.title}</h1>
        <p className="mt-1 text-muted-foreground">Organize your research outline</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="font-serif">Outline Structure</CardTitle>
              <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" className="gap-2" onClick={() => openAddDialog(null)}>
                    <Plus className="h-4 w-4" />
                    Add Section
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Section</DialogTitle>
                    <DialogDescription>
                      Create a new section in your outline.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Title</label>
                      <Input
                        placeholder="Section title..."
                        value={newSectionTitle}
                        onChange={(e) => setNewSectionTitle(e.target.value)}
                        autoFocus
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Type</label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" className="w-full justify-start">
                            {newSectionType}
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          {sectionTypes.map((type) => (
                            <DropdownMenuItem
                              key={type}
                              onClick={() => setNewSectionType(type)}
                            >
                              {type}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleAddSection} disabled={createMutation.isPending}>
                      Add Section
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {tree.length > 0 ? (
                <div className="space-y-1">
                  {tree.map((section) => (
                    <SectionItem
                      key={section.id}
                      section={section}
                      onAddChild={openAddDialog}
                      onDelete={(id) => deleteMutation.mutate(id)}
                    />
                  ))}
                </div>
              ) : (
                <div className="py-12 text-center">
                  <FileText className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
                  <h3 className="mb-2 font-serif text-lg font-semibold">No sections yet</h3>
                  <p className="mb-4 text-sm text-muted-foreground">
                    Start building your outline by adding sections.
                  </p>
                  <Button size="sm" onClick={() => openAddDialog(null)}>
                    <Plus className="mr-2 h-4 w-4" />
                    Add First Section
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 font-serif">
                <Sparkles className="h-4 w-4 text-primary" />
                AI Suggestions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                AI-powered section suggestions coming soon. This will analyze your research
                topic and suggest relevant sections.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

