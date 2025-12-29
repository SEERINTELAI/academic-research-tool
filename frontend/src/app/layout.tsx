import type { Metadata } from "next";
import { Crimson_Pro, Source_Sans_3, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { Toaster } from "@/components/ui/sonner";
import { DiagnosticsPanel } from "@/components/diagnostics-panel";

const crimsonPro = Crimson_Pro({
  subsets: ["latin"],
  variable: "--font-crimson",
  display: "swap",
});

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Scholar - Academic Research Tool",
  description: "AI-powered academic paper writing assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`min-h-screen ${crimsonPro.variable} ${sourceSans.variable} ${jetbrainsMono.variable}`}>
        <Providers>
          <SidebarProvider>
            <AppSidebar />
            <SidebarInset>
              <main className="flex-1">
                {children}
              </main>
            </SidebarInset>
          </SidebarProvider>
          <Toaster />
          <DiagnosticsPanel />
        </Providers>
      </body>
    </html>
  );
}
