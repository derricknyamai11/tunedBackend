from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING, Any
from datetime import datetime
from tuned.dtos.content import TagResponseDTO
from tuned.dtos.base import BaseDTO, PaginationDTO

if TYPE_CHECKING:
    from tuned.models.blog import BlogCategory, BlogPost, BlogComment, CommentReaction


@dataclass
class BlogCategoryDTO(BaseDTO):
    name: str
    slug: str
    description: str 

@dataclass
class BlogCategoryResponseDTO(BaseDTO):
    id: str
    name: str
    slug: str
    description: Optional[str]

    @classmethod
    def from_model(cls, obj: "BlogCategory") -> "BlogCategoryResponseDTO":
        return cls(
            id=str(obj.id),
            name=obj.name,
            slug=obj.slug,
            description=obj.description,
        )

@dataclass
class BlogPostDTO(BaseDTO):
    title: str
    content: str
    author: str
    category_id: str
    excerpt: str = ""
    featured_image: str = ""
    meta_description: str = ""
    is_published: bool = False
    is_featured: bool = False
    slug: Optional[str] = None
    published_at: Optional[datetime] = None

@dataclass
class BlogPostResponseDTO(BaseDTO):
    id: str
    title: str
    content: str
    author: str
    category_id: Optional[str]
    slug: str
    excerpt: str
    featured_image: str
    meta_description: str
    is_published: bool
    is_featured: bool
    published_at: str
    comments: List[BlogCommentResponseDTO]
    tags: List[TagResponseDTO]

    @classmethod
    def from_model(cls, obj: "BlogPost") -> "BlogPostResponseDTO":
        return cls(
            id=obj.id,
            title=obj.title,
            content=obj.content,
            author=obj.author,
            category_id=obj.category_id,
            slug=obj.slug,
            excerpt=obj.excerpt or "",
            featured_image=obj.featured_image or "",
            meta_description=obj.meta_description or "",
            is_published=obj.is_published,
            is_featured=obj.is_featured,
            published_at=obj.published_at.isoformat() if obj.published_at else "",
            comments=[BlogCommentResponseDTO.from_model(comment) for comment in obj.comments],
            tags=[TagResponseDTO.from_model(tag) for tag in obj.tag_list],
        )

@dataclass
class BlogPostListResponseDTO(PaginationDTO):
    blogs: List[BlogPostResponseDTO]
    total: int

    @classmethod
    def from_model(cls, obj: Any) -> "BlogPostListResponseDTO":
        return cls(
            blogs=[BlogPostResponseDTO.from_model(blog) for blog in obj.blogs],
            total=obj.total,
            sort=obj.sort,
            order=obj.order,
            page=obj.page,
            per_page=obj.per_page,
        )

@dataclass
class BlogPostListRequestDTO(PaginationDTO):
    q: Optional[str] = None
    category_id: Optional[str] = None
    is_published: Optional[bool] = None

@dataclass
class BlogCommentDTO(BaseDTO):
    post_id: str
    content: str
    name: str = ""
    email: str = ""
    user_id: Optional[str] = None
    approved: bool = False

@dataclass
class BlogCommentResponseDTO(BaseDTO):
    id: str
    post_id: str
    content: str
    name: Optional[str] = ""
    email: Optional[str] = ""
    user_id: Optional[str] = None
    approved: bool = False
    reactions: List[CommentReactionResponseDTO] = field(default_factory=list)
    total_likes: int = 0
    total_dislikes: int = 0

    @classmethod
    def from_model(cls, obj: "BlogComment") -> "BlogCommentResponseDTO":
        return cls(
            id=str(obj.id),
            post_id=str(obj.post_id),
            content=obj.content,
            name=obj.name,
            email=obj.email,
            user_id=str(obj.user_id) if obj.user_id else None,
            approved=obj.approved,
            reactions=[CommentReactionResponseDTO.from_model(reaction) for reaction in obj.reactions],
            total_likes=obj.total_likes,
            total_dislikes=obj.total_dislikes,
        )

@dataclass
class CommentReactionDTO(BaseDTO):
    comment_id: str
    reaction_type: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None  

@dataclass
class CommentReactionResponseDTO(BaseDTO):
    id: str
    comment_id: str
    reaction_type: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None

    @classmethod
    def from_model(cls, obj: "CommentReaction") -> "CommentReactionResponseDTO":
        return cls(
            id=str(obj.id),
            comment_id=str(obj.comment_id),
            reaction_type=obj.reaction_type,
            user_id=str(obj.user_id),
            ip_address=obj.ip_address,
        )

@dataclass
class PostByCategoryRequestDTO:
    category_id: str
    exclude: str
    per_page: int = 3