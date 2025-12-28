"""
Outline Section API routes.

CRUD operations for hierarchical research outlines.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.deps import CurrentUser, DatabaseDep
from src.models.outline import (
    OutlineSectionCreate,
    OutlineSectionReorder,
    OutlineSectionResponse,
    OutlineSectionUpdate,
    OutlineSectionWithChildren,
    OutlineTree,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_tree(sections: list[dict], parent_id: Optional[str] = None) -> list[OutlineSectionWithChildren]:
    """
    Build a nested tree structure from flat section list.
    
    Args:
        sections: Flat list of section dicts from database
        parent_id: Parent ID to filter by (None for root level)
    
    Returns:
        List of sections with nested children
    """
    result = []
    
    for section in sections:
        section_parent = section.get("parent_id")
        
        if section_parent == parent_id:
            # This section belongs at this level
            children = _build_tree(sections, section["id"])
            
            result.append(OutlineSectionWithChildren(
                id=section["id"],
                project_id=section["project_id"],
                parent_id=section["parent_id"],
                title=section["title"],
                section_type=section["section_type"],
                questions=section.get("questions") or [],
                notes=section.get("notes"),
                order_index=section["order_index"],
                created_at=section["created_at"],
                updated_at=section["updated_at"],
                children=children,
            ))
    
    # Sort by order_index
    result.sort(key=lambda x: x.order_index)
    
    return result


@router.get(
    "",
    response_model=OutlineTree,
    summary="Get project outline",
    description="Get the complete outline tree for a project.",
)
async def get_outline(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> OutlineTree:
    """Get the complete outline tree for a project."""
    try:
        # Verify project exists
        project_result = db.table("project")\
            .select("id")\
            .eq("id", str(project_id))\
            .maybe_single()\
            .execute()
        
        if not project_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        
        # Get all sections for the project
        result = db.table("outline_section")\
            .select("*")\
            .eq("project_id", str(project_id))\
            .order("order_index")\
            .execute()
        
        sections = result.data or []
        tree = _build_tree(sections)
        
        return OutlineTree(
            project_id=project_id,
            sections=tree,
            total_count=len(sections),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting outline for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.post(
    "",
    response_model=OutlineSectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create outline section",
    description="Add a new section to the project outline.",
)
async def create_section(
    project_id: UUID,
    section: OutlineSectionCreate,
    user: CurrentUser,
    db: DatabaseDep,
) -> OutlineSectionResponse:
    """Create a new outline section."""
    try:
        # Verify project exists
        project_result = db.table("project")\
            .select("id")\
            .eq("id", str(project_id))\
            .maybe_single()\
            .execute()
        
        if not project_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        
        # If order_index not provided, append to end
        order_index = section.order_index
        if order_index is None:
            # Get max order_index for siblings
            siblings_query = db.table("outline_section")\
                .select("order_index")\
                .eq("project_id", str(project_id))
            
            if section.parent_id:
                siblings_query = siblings_query.eq("parent_id", str(section.parent_id))
            else:
                siblings_query = siblings_query.is_("parent_id", "null")
            
            siblings_result = siblings_query.execute()
            
            if siblings_result.data:
                max_index = max(s["order_index"] for s in siblings_result.data)
                order_index = max_index + 1
            else:
                order_index = 0
        
        # Create the section
        insert_data = {
            "project_id": str(project_id),
            "title": section.title,
            "section_type": section.section_type.value,
            "questions": section.questions,
            "notes": section.notes,
            "order_index": order_index,
        }
        
        if section.parent_id:
            insert_data["parent_id"] = str(section.parent_id)
        
        result = db.table("outline_section").insert(insert_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create section",
            )
        
        created = result.data[0]
        logger.info(f"Created outline section {created['id']} for project {project_id}")
        
        return OutlineSectionResponse(**created)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating section: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "/{section_id}",
    response_model=OutlineSectionResponse,
    summary="Get outline section",
    description="Get details of a specific outline section.",
)
async def get_section(
    project_id: UUID,
    section_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> OutlineSectionResponse:
    """Get a specific outline section."""
    try:
        result = db.table("outline_section")\
            .select("*")\
            .eq("id", str(section_id))\
            .eq("project_id", str(project_id))\
            .maybe_single()\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found",
            )
        
        return OutlineSectionResponse(**result.data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting section {section_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.patch(
    "/{section_id}",
    response_model=OutlineSectionResponse,
    summary="Update outline section",
    description="Update an outline section's details.",
)
async def update_section(
    project_id: UUID,
    section_id: UUID,
    section_update: OutlineSectionUpdate,
    user: CurrentUser,
    db: DatabaseDep,
) -> OutlineSectionResponse:
    """Update an outline section."""
    # Build update dict with only non-None fields
    update_data = section_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    
    # Convert enums/UUIDs for database
    if "section_type" in update_data and update_data["section_type"]:
        update_data["section_type"] = update_data["section_type"].value
    if "parent_id" in update_data and update_data["parent_id"]:
        update_data["parent_id"] = str(update_data["parent_id"])
    
    try:
        result = db.table("outline_section")\
            .update(update_data)\
            .eq("id", str(section_id))\
            .eq("project_id", str(project_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found",
            )
        
        logger.info(f"Updated outline section {section_id}")
        return OutlineSectionResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating section {section_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.delete(
    "/{section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete outline section",
    description="Delete an outline section and its children.",
)
async def delete_section(
    project_id: UUID,
    section_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> None:
    """Delete an outline section (cascades to children)."""
    try:
        result = db.table("outline_section")\
            .delete()\
            .eq("id", str(section_id))\
            .eq("project_id", str(project_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found",
            )
        
        logger.info(f"Deleted outline section {section_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting section {section_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.post(
    "/reorder",
    response_model=OutlineTree,
    summary="Reorder outline sections",
    description="Move sections within the outline tree.",
)
async def reorder_sections(
    project_id: UUID,
    reorder: OutlineSectionReorder,
    user: CurrentUser,
    db: DatabaseDep,
) -> OutlineTree:
    """Reorder/reparent an outline section."""
    try:
        update_data = {"order_index": reorder.new_order_index}
        
        if reorder.new_parent_id:
            update_data["parent_id"] = str(reorder.new_parent_id)
        else:
            # Moving to root level - need to set parent_id to null
            update_data["parent_id"] = None
        
        result = db.table("outline_section")\
            .update(update_data)\
            .eq("id", str(reorder.section_id))\
            .eq("project_id", str(project_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found",
            )
        
        logger.info(f"Reordered section {reorder.section_id} to index {reorder.new_order_index}")
        
        # Return updated tree
        return await get_outline(project_id, user, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error reordering section {reorder.section_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

