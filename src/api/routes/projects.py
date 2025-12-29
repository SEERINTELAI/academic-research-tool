"""
Project API routes.

CRUD operations for research projects.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.deps import CurrentUser, DatabaseDep
from src.models.project import (
    ProjectCreate,
    ProjectListItem,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new research project for the authenticated user.",
)
async def create_project(
    project: ProjectCreate,
    user: CurrentUser,
    db: DatabaseDep,
) -> ProjectResponse:
    """Create a new research project."""
    try:
        result = db.table("project").insert({
            "title": project.title,
            "description": project.description,
            "status": ProjectStatus.DRAFT.value,
        }).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create project",
            )
        
        created = result.data[0]
        logger.info(f"Created project {created['id']} for user {user.user_id}")
        
        return ProjectResponse(**created)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "",
    response_model=list[ProjectListItem],
    summary="List projects",
    description="List all projects for the authenticated user.",
)
async def list_projects(
    user: CurrentUser,
    db: DatabaseDep,
    status_filter: Optional[ProjectStatus] = Query(
        None, 
        alias="status",
        description="Filter by project status",
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[ProjectListItem]:
    """List user's projects with optional filtering."""
    from src.config import get_settings
    settings = get_settings()
    
    try:
        query = db.table("project").select("*")
        
        # Apply status filter if provided
        if status_filter:
            query = query.eq("status", status_filter.value)
        
        # Order by updated_at descending (most recent first)
        query = query.order("updated_at", desc=True)
        
        # Pagination
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        
        # Convert to response models
        projects = []
        for row in result.data:
            projects.append(ProjectListItem(
                id=row["id"],
                title=row["title"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                source_count=0,  # TODO: Add aggregate query
                outline_section_count=0,  # TODO: Add aggregate query
            ))
        
        return projects
        
    except Exception as e:
        logger.exception(f"Error listing projects: {e}")
        
        # In development mode with unconfigured database, return empty list
        # instead of failing so the frontend can still load
        if settings.is_development and "your-project.supabase.co" in settings.supabase_url:
            logger.warning("Database not configured - returning empty project list for development")
            return []
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project",
    description="Get details of a specific project.",
)
async def get_project(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> ProjectResponse:
    """Get project details."""
    try:
        result = db.table("project")\
            .select("*")\
            .eq("id", str(project_id))\
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        
        return ProjectResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
    description="Update project details.",
)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    user: CurrentUser,
    db: DatabaseDep,
) -> ProjectResponse:
    """Update project details."""
    # Build update dict with only non-None fields
    update_data = project_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    
    # Convert enum to string for database
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value
    
    try:
        result = db.table("project")\
            .update(update_data)\
            .eq("id", str(project_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        
        logger.info(f"Updated project {project_id}")
        return ProjectResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    description="Soft-delete a project by setting status to archived.",
)
async def delete_project(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    hard_delete: bool = Query(False, description="Permanently delete instead of archiving"),
) -> None:
    """Delete or archive a project."""
    try:
        if hard_delete:
            # Permanent deletion (cascades to related records)
            result = db.table("project")\
                .delete()\
                .eq("id", str(project_id))\
                .execute()
            
            logger.info(f"Hard deleted project {project_id}")
        else:
            # Soft delete by archiving
            result = db.table("project")\
                .update({"status": ProjectStatus.ARCHIVED.value})\
                .eq("id", str(project_id))\
                .execute()
            
            logger.info(f"Archived project {project_id}")
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

