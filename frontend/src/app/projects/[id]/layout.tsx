'use client';

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuthStore, useProjectStore, useSourcesStore, useOutlineStore } from '@/lib/store';
import { Skeleton } from '@/components/ui/skeleton';

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const projectId = params.id as string;
  
  const token = useAuthStore((s) => s.token);
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject);
  const setSources = useSourcesStore((s) => s.setSources);
  const setSections = useOutlineStore((s) => s.setSections);

  const authToken = token || 'demo-token';

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(authToken, projectId),
    enabled: !!projectId,
  });

  const { data: sources } = useQuery({
    queryKey: ['sources', projectId],
    queryFn: () => api.listSources(authToken, projectId),
    enabled: !!projectId,
  });

  const { data: outline } = useQuery({
    queryKey: ['outline', projectId],
    queryFn: () => api.getOutline(authToken, projectId),
    enabled: !!projectId,
  });

  useEffect(() => {
    if (project) {
      setCurrentProject(project);
    }
    return () => {
      setCurrentProject(null);
    };
  }, [project, setCurrentProject]);

  useEffect(() => {
    if (sources) {
      setSources(sources);
    }
  }, [sources, setSources]);

  useEffect(() => {
    if (outline) {
      // API returns {project_id, sections, total_count} - extract just the sections array
      const sections = Array.isArray(outline) ? outline : outline.sections || [];
      setSections(sections);
    }
  }, [outline, setSections]);

  if (projectLoading) {
    return (
      <div className="p-6">
        <div className="mb-6 space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="text-center">
          <h2 className="mb-2 font-serif text-2xl font-semibold">Project Not Found</h2>
          <p className="text-muted-foreground">The project you&apos;re looking for doesn&apos;t exist.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

