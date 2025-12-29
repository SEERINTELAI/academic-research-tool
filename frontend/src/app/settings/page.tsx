'use client';

import { Moon, Sun, Monitor } from 'lucide-react';
import { useUIStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export default function SettingsPage() {
  const { theme, setTheme } = useUIStore();

  const themeOptions = [
    { value: 'light' as const, label: 'Light', icon: Sun },
    { value: 'dark' as const, label: 'Dark', icon: Moon },
    { value: 'system' as const, label: 'System', icon: Monitor },
  ];

  return (
    <div className="page-transition p-6">
      <div className="mb-8">
        <h1 className="font-serif text-3xl font-bold">Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Manage your preferences and account settings
        </p>
      </div>

      <div className="max-w-2xl space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="font-serif">Appearance</CardTitle>
            <CardDescription>
              Customize how the application looks on your device.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="mb-3 block text-sm font-medium">Theme</label>
                <div className="flex gap-2">
                  {themeOptions.map((option) => (
                    <Button
                      key={option.value}
                      variant={theme === option.value ? 'default' : 'outline'}
                      className="flex-1 gap-2"
                      onClick={() => setTheme(option.value)}
                    >
                      <option.icon className="h-4 w-4" />
                      {option.label}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="font-serif">Account</CardTitle>
            <CardDescription>
              Manage your account and authentication.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Authentication settings coming soon. Currently using demo mode.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="font-serif">API Configuration</CardTitle>
            <CardDescription>
              Configure connections to external services.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Backend API</p>
                <p className="text-sm text-muted-foreground">
                  {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                </p>
              </div>
              <Button variant="outline" size="sm" disabled>
                Configure
              </Button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Hyperion RAG</p>
                <p className="text-sm text-muted-foreground">Connected via backend</p>
              </div>
              <Button variant="outline" size="sm" disabled>
                Status
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="font-serif">About</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              <strong>Scholar</strong> - AI-powered Academic Research Tool
            </p>
            <p>Version: 0.1.0 (MVP)</p>
            <p>
              Built with Next.js, FastAPI, Hyperion RAG, and LightRAG.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

