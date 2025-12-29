/**
 * Test page with server-side data fetching.
 * This page fetches data on the server, so it works even without JavaScript.
 */

import Link from 'next/link';

interface Project {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
}

async function getProjects(): Promise<Project[]> {
  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8003';
    const response = await fetch(`${API_URL}/api/projects`, {
      headers: {
        'Authorization': 'Bearer demo-token',
        'Content-Type': 'application/json',
      },
      cache: 'no-store', // Always fetch fresh data
    });
    
    if (!response.ok) {
      console.error('[SSR] Failed to fetch projects:', response.status);
      return [];
    }
    
    return await response.json();
  } catch (error) {
    console.error('[SSR] Error fetching projects:', error);
    return [];
  }
}

export default async function TestSSRPage() {
  const projects = await getProjects();
  
  return (
    <div className="p-6">
      <div className="mb-4 p-3 bg-green-100 dark:bg-green-900 rounded">
        <p className="font-bold">✅ Server-Side Rendered Page</p>
        <p className="text-sm">This page fetches data on the server (no JavaScript required)</p>
        <p className="text-sm">Found {projects.length} projects</p>
      </div>
      
      <h1 className="text-2xl font-bold mb-4">Projects (SSR)</h1>
      
      {projects.length === 0 ? (
        <p className="text-gray-500">No projects found</p>
      ) : (
        <ul className="space-y-2">
          {projects.slice(0, 10).map((project) => (
            <li key={project.id} className="p-3 bg-gray-100 dark:bg-gray-800 rounded">
              <strong>{project.title}</strong>
              <span className="ml-2 text-xs text-gray-500">{project.status}</span>
            </li>
          ))}
          {projects.length > 10 && (
            <li className="text-gray-500 text-sm">...and {projects.length - 10} more</li>
          )}
        </ul>
      )}
      
      <div className="mt-6">
        <Link href="/projects" className="text-blue-500 underline">
          Go to full Projects page (requires JavaScript)
        </Link>
      </div>
    </div>
  );
}

