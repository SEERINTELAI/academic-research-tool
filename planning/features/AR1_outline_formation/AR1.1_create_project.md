# AR1.1: Create Project with Outline

**Status**: pending  
**Priority**: P0  
**Depends On**: None  
**Blocks**: AR1.2, AR2.*, AR3.*, AR4.*, AR5.*  
**Estimated Hours**: 6

## Summary

Create a new research project with a basic outline structure. This is the entry point for all user activity.

## Acceptance Criteria

- [ ] Create project with title and optional description
- [ ] Initialize empty outline structure
- [ ] Store in Supabase with user ownership
- [ ] Return project ID for subsequent operations
- [ ] List user's projects with basic metadata

## Database Schema

```sql
CREATE TABLE project (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL,  -- Supabase auth user ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'active'  -- active, archived, deleted
);

CREATE INDEX idx_project_owner ON project(owner_id);
CREATE INDEX idx_project_status ON project(status);

-- Row level security
ALTER TABLE project ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own projects" ON project
    FOR SELECT USING (auth.uid() = owner_id);

CREATE POLICY "Users can create projects" ON project
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Users can update own projects" ON project
    FOR UPDATE USING (auth.uid() = owner_id);
```

## API Design

### Create Project

```
POST /api/projects
Authorization: Bearer {supabase_token}
```

Request:
```json
{
  "title": "Literature Review on Machine Learning",
  "description": "Optional project description"
}
```

Response:
```json
{
  "id": "uuid",
  "title": "Literature Review on Machine Learning",
  "description": "Optional project description",
  "created_at": "2024-01-15T10:00:00Z",
  "status": "active"
}
```

### List Projects

```
GET /api/projects
GET /api/projects?status=active
Authorization: Bearer {supabase_token}
```

Response:
```json
{
  "projects": [
    {
      "id": "uuid",
      "title": "Literature Review on Machine Learning",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z",
      "status": "active",
      "source_count": 5,
      "word_count": 2500
    }
  ]
}
```

### Get Project

```
GET /api/projects/{project_id}
```

## Implementation

### Pydantic Models

```python
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    status: str

class ProjectListItem(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    status: str
    source_count: int = 0
    word_count: int = 0
```

### API Route

```python
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from ..models.project import ProjectCreate, ProjectResponse, ProjectListItem
from ..services.auth import get_current_user
from ..services.database import supabase

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.post("", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    user_id: UUID = Depends(get_current_user)
):
    """Create a new research project."""
    result = supabase.table("project").insert({
        "title": project.title,
        "description": project.description,
        "owner_id": str(user_id)
    }).execute()
    
    if not result.data:
        raise HTTPException(500, "Failed to create project")
    
    return result.data[0]

@router.get("", response_model=list[ProjectListItem])
async def list_projects(
    status: str = "active",
    user_id: UUID = Depends(get_current_user)
):
    """List user's projects."""
    result = supabase.table("project")\
        .select("*")\
        .eq("owner_id", str(user_id))\
        .eq("status", status)\
        .order("updated_at", desc=True)\
        .execute()
    
    return result.data

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user)
):
    """Get project details."""
    result = supabase.table("project")\
        .select("*")\
        .eq("id", str(project_id))\
        .eq("owner_id", str(user_id))\
        .single()\
        .execute()
    
    if not result.data:
        raise HTTPException(404, "Project not found")
    
    return result.data
```

## Testing

```python
@pytest.mark.asyncio
async def test_create_project():
    """Test project creation."""
    response = await client.post(
        "/api/projects",
        json={"title": "Test Project"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Project"
    assert data["status"] == "active"

@pytest.mark.asyncio
async def test_list_projects_filtered():
    """Test project listing with filter."""
    # Create active and archived projects
    await create_project("Active", status="active")
    await create_project("Archived", status="archived")
    
    response = await client.get(
        "/api/projects?status=active",
        headers=auth_headers
    )
    
    projects = response.json()["projects"]
    assert all(p["status"] == "active" for p in projects)
```

## Files to Create

| File | Action |
|------|--------|
| `src/models/project.py` | Create |
| `src/api/routes/projects.py` | Create |
| `src/services/database.py` | Create (Supabase client) |

## Notes

- This is the foundation for all other features
- RLS ensures users only see their own projects
- Consider adding project templates in future

