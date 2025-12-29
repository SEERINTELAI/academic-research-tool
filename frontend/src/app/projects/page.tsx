'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { FolderOpen, Plus, MoreHorizontal, Archive, Trash2 } from 'lucide-react';
import { api, Project } from '@/lib/api';
import { useAuthStore, useProjectStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';


function ProjectCard({ project }: { project: Project }) {
  const statusColors: Record<string, string> = {
    draft: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400',
    active: 'bg-green-500/10 text-green-700 dark:text-green-400',
    archived: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    completed: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  };

  return (
    <Card className="group relative transition-colors hover:border-primary/30">
      <Link href={`/projects/${project.id}/outline`} className="absolute inset-0 z-0" />
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <FolderOpen className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="font-serif text-lg">{project.title}</CardTitle>
              <CardDescription className="text-xs">
                Updated {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}
              </CardDescription>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="relative z-10 h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100"
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Archive className="mr-2 h-4 w-4" />
                Archive
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        {project.description && (
          <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">
            {project.description}
          </p>
        )}
        <Badge variant="secondary" className={statusColors[project.status]}>
          {project.status}
        </Badge>
      </CardContent>
    </Card>
  );
}

function ProjectsSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <Card key={i}>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="space-y-2">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Skeleton className="mb-3 h-10 w-full" />
            <Skeleton className="h-5 w-16" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function ProjectsPage() {
  const token = useAuthStore((s) => s.token);
  const setProjects = useProjectStore((s) => s.setProjects);

  // For demo purposes, use a mock token if not set
  const authToken = token || 'demo-token';

  const { data: projects, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      console.log('[Projects] Fetching projects with token:', authToken);
      const result = await api.listProjects(authToken);
      console.log('[Projects] Fetched', result?.length, 'projects');
      return result;
    },
    enabled: !!authToken,
    retry: 1, // Only retry once to avoid appearing stuck
    retryDelay: 1000, // 1 second between retries
  });

  // Debug logging
  console.log('[Projects] Render state:', { isLoading, error, projectsCount: projects?.length, authToken });

  useEffect(() => {
    if (projects) {
      setProjects(projects);
    }
  }, [projects, setProjects]);

  return (
    <div className="page-transition p-6">
      {/* Debug Status Banner - remove after debugging */}
      <div className="mb-4 p-2 text-xs bg-gray-100 dark:bg-gray-800 rounded font-mono">
        Status: {isLoading ? '⏳ Loading...' : error ? '❌ Error' : `✅ ${projects?.length ?? 0} projects`}
        {error && <span className="text-red-500 ml-2">{String(error)}</span>}
      </div>
      
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="font-serif text-3xl font-bold">Projects</h1>
          <p className="mt-1 text-muted-foreground">Manage your research projects</p>
        </div>
        <Button asChild className="gap-2">
          <Link href="/projects/new">
            <Plus className="h-4 w-4" />
            New Project
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <ProjectsSkeleton />
      ) : error ? (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="py-8 text-center">
            <p className="text-destructive font-medium">Failed to load projects</p>
            <p className="text-sm text-muted-foreground mt-2">
              {error instanceof Error ? error.message : 'An unknown error occurred'}
            </p>
            <p className="text-xs text-muted-foreground mt-4">
              Check that the backend is running at {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}
            </p>
          </CardContent>
        </Card>
      ) : projects && projects.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center">
            <FolderOpen className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
            <h3 className="mb-2 font-serif text-xl font-semibold">No projects yet</h3>
            <p className="mb-6 text-muted-foreground">
              Create your first research project to get started.
            </p>
            <Button asChild>
              <Link href="/projects/new">Create Project</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

