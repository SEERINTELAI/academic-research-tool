# Academic Research Tool - Frontend

Next.js 16 frontend for the Academic Research Tool.

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Styling**: Tailwind CSS v4 + shadcn/ui
- **Editor**: Monaco Editor (@monaco-editor/react)
- **State**: Zustand (persist to localStorage)
- **Data Fetching**: TanStack React Query
- **Icons**: Lucide React

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

The app runs at http://localhost:3000

## Environment Variables

Create `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Landing page
│   ├── projects/          # Project management
│   │   ├── page.tsx       # Project list
│   │   ├── new/           # Create project
│   │   └── [id]/          # Project views
│   │       ├── layout.tsx # Project layout wrapper
│   │       ├── outline/   # Outline editor
│   │       ├── sources/   # Sources library
│   │       ├── write/     # Monaco editor + AI assist
│   │       └── research/  # RAG chat interface
│   ├── search/            # Global paper search
│   └── settings/          # App settings
├── components/
│   ├── ui/               # shadcn/ui components
│   ├── app-sidebar.tsx   # Navigation sidebar
│   └── providers.tsx     # React Query + Theme providers
└── lib/
    ├── api.ts            # Backend API client
    ├── store.ts          # Zustand stores
    └── utils.ts          # Utilities (cn, etc.)
```

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page with feature overview |
| `/projects` | List all projects |
| `/projects/new` | Create new project |
| `/projects/[id]/outline` | Edit project outline |
| `/projects/[id]/sources` | Manage paper sources |
| `/projects/[id]/write` | Monaco editor with AI assist |
| `/projects/[id]/research` | Chat with your papers (RAG) |
| `/search` | Search academic papers |
| `/settings` | Theme and preferences |

## Key Features

### Monaco Editor (`/write`)
- Full markdown editing
- Serif font (Crimson Pro) for academic feel
- AI Writing Assist panel (uses `/research/query`)
- Citation insertion from sources sidebar
- Keyboard shortcuts (Cmd+S to save)

### Sources Library (`/sources`)
- Semantic Scholar search integration
- Add papers to project
- Trigger PDF ingestion to LightRAG
- Discovery panel (references, citations, similar papers)

### Research Chat (`/research`)
- RAG-powered Q&A over ingested papers
- Multiple query modes (hybrid, local, global, naive)
- Source attribution with expandable chunks
- Suggested questions

## Theme

Custom "warm paper" aesthetic:
- **Light mode**: Cream/paper tones, deep blue-green accents
- **Dark mode**: Deep library blue, muted gold accents
- **Typography**: Crimson Pro (serif) for headings, Source Sans (sans) for body

## API Integration

The frontend expects a FastAPI backend at `NEXT_PUBLIC_API_URL` with these endpoints:

- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}/outline` - Get outline sections
- `GET /api/v1/projects/{id}/sources` - List sources
- `GET /api/v1/sources/search?query=...` - Search papers
- `POST /api/v1/projects/{id}/sources/{sid}/ingest` - Ingest source
- `POST /api/v1/projects/{id}/research/query` - RAG query
- `GET /api/v1/projects/{id}/sources/{sid}/discover` - Discovery

See `src/lib/api.ts` for full TypeScript types.

## Development

```bash
# Type checking
npm run lint

# Production build
npm run build
npm start
```
