'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BookOpen,
  FolderOpen,
  MessageSquare,
  Plus,
  Settings,
  Sparkles,
} from 'lucide-react';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import { useProjectStore } from '@/lib/store';

const navItems = [
  { title: 'Projects', icon: FolderOpen, href: '/projects' },
];

export function AppSidebar() {
  const pathname = usePathname();
  const currentProject = useProjectStore((s) => s.currentProject);

  // Simplified: just Research and Write
  // Outline and Sources are accessible within the Research tab
  const projectNavItems = currentProject
    ? [
        { title: 'Research', icon: MessageSquare, href: `/projects/${currentProject.id}/research` },
        { title: 'Write', icon: BookOpen, href: `/projects/${currentProject.id}/write` },
      ]
    : [];

  return (
    <Sidebar>
      <SidebarHeader className="border-b border-sidebar-border px-4 py-3">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-serif text-lg font-semibold">Scholar</span>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={pathname === item.href}>
                    <Link href={item.href}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {currentProject && (
          <SidebarGroup>
            <SidebarGroupLabel className="flex items-center justify-between">
              <span className="truncate">{currentProject.title}</span>
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {projectNavItems.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={pathname === item.href}>
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {!currentProject && (
          <SidebarGroup>
            <SidebarGroupLabel>Quick Start</SidebarGroupLabel>
            <SidebarGroupContent className="px-2">
              <Button asChild variant="outline" size="sm" className="w-full justify-start gap-2">
                <Link href="/projects/new">
                  <Plus className="h-4 w-4" />
                  New Project
                </Link>
              </Button>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border p-2">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild isActive={pathname === '/settings'}>
              <Link href="/settings">
                <Settings className="h-4 w-4" />
                <span>Settings</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}

