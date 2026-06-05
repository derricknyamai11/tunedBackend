from typing import Any, Sequence
from sqlalchemy import select, or_, asc, desc, func
from tuned.models import BlogPost
from tuned.dtos import BlogPostDTO, BlogPostResponseDTO, BlogPostListRequestDTO, BlogPostListResponseDTO, PostByCategoryRequestDTO
from tuned.repository.exceptions import NotFound, DatabaseError, AlreadyExists
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime, timezone
from tuned.repository.blogs.helper import handle_tags

class CreateBlog:
    def __init__(self, session: Session):
        self.session = session

    def execute(self, data: BlogPostDTO) -> BlogPostResponseDTO:
        try:
            data_dict = data.__dict__.copy()
            tags_list = data_dict.pop("tags", [])
            post = BlogPost(**data_dict)

            self.session.add(post)
            self.session.flush()

            tags_obj = handle_tags(tags_list, self.session)
            post.tags = tags_obj
            self.session.flush()

            return BlogPostResponseDTO.from_model(post)

        except IntegrityError as e:
            raise AlreadyExists("Post already exists")
        except SQLAlchemyError as e:
            raise DatabaseError(f"Database error while creating post:\n {str(e)}")

class GetBlogPostBySlug:
    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(self, slug: str) -> BlogPostResponseDTO:
        try:
            stmt = select(BlogPost).where(BlogPost.slug == slug)
            post = self.session.scalar(stmt)
            if not post:
                raise NotFound("post not found")

            return BlogPostResponseDTO.from_model(post)

        except SQLAlchemyError as e:
            raise DatabaseError(f"Database error while fetching post: {str(e)}")

class GetBlogPostByID:
    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(self, id: str) -> BlogPostResponseDTO:
        try:
            stmt = select(BlogPost).where(BlogPost.id == id)
            post = self.session.scalar(stmt)
            if not post:
                raise NotFound("post not found")

            return BlogPostResponseDTO.from_model(post)

        except SQLAlchemyError as e:
            raise DatabaseError(f"Database error while fetching post: {str(e)}")

class GetFeaturedBlogPosts:
    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(self) -> list[BlogPostResponseDTO]:
        try:
            stmt = (
                select(BlogPost)
                .where(BlogPost.is_featured == True, BlogPost.is_published == True)
                .order_by(BlogPost.published_at.desc())
            )
            posts = self.session.scalars(stmt).all()
            return [BlogPostResponseDTO.from_model(s) for s in posts]

        except SQLAlchemyError as e:
            raise DatabaseError(f"Database error while fetching posts: {str(e)}")

class GetPublishedBlogPosts:
    def __init__(self, session: Session, req: BlogPostListRequestDTO) -> None:
        self.session = session
        self.req = req
    
    def execute(self) -> BlogPostListResponseDTO:
        try:
            stmt = select(BlogPost).where(BlogPost.is_published == True)
            return getBlogPostListResponse(self.session, stmt, self.req)

        except SQLAlchemyError as e:
            raise DatabaseError(f"Database error while fetching posts: {str(e)}")

class UpdateOrDeleteBlogPost:
    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(self, id: str, data: BlogPostDTO) -> BlogPostResponseDTO:
        try:
            stmt = select(BlogPost).where(BlogPost.id == id)
            post = self.session.scalar(stmt)
            if not post:
                raise NotFound("post not found")
            
            if data.is_deleted:
                post.is_deleted = data.is_deleted
                post.deleted_at = datetime.now(timezone.utc)
                post.deleted_by = data.deleted_by
            else:
                if data.title:
                    post.title = data.title
                if data.content:
                    post.content = data.content
                if data.excerpt:
                    post.excerpt = data.excerpt
                if data.featured_image:
                    post.featured_image = data.featured_image
                if data.author:
                    post.author = data.author
                if data.category_id:
                    post.category_id = data.category_id
                if data.meta_description:
                    post.meta_description = data.meta_description
                if data.is_published:
                    post.is_published = data.is_published
                    post.published_at = datetime.now(timezone.utc)
                if data.is_featured:
                    post.is_featured = data.is_featured
                if data.updated_at:
                    post.updated_at = data.updated_at
                if data.updated_by:
                    post.updated_by = data.updated_by
            
            self.session.add(post)
            self.session.flush()
            if hasattr(data, "tags") and getattr(data, "tags"):
                tags_obj = handle_tags(getattr(data, "tags"), self.session)
                post.tags = tags_obj
                self.session.flush()

            return BlogPostResponseDTO.from_model(post)

        except SQLAlchemyError as e:
            raise DatabaseError(f"Database error while updating post: {str(e)}")   

def getBlogPostListResponse(
    session: Session, stmt: Any, req: BlogPostListRequestDTO
) -> BlogPostListResponseDTO:
    if req.category_id:
        stmt = stmt.where(BlogPost.category_id == req.category_id)
        
    if req.q:
        search_pattern = f"%{req.q}%"
        stmt = stmt.where(
            or_(
                BlogPost.title.ilike(search_pattern),
                BlogPost.excerpt.ilike(search_pattern),
                BlogPost.content.ilike(search_pattern)
            )
        )

    sort_map = {
        "published_at": BlogPost.published_at,
        "created_at": BlogPost.created_at,
        "title": BlogPost.title,
    }

    sort_field = sort_map.get(req.sort or "created_at", BlogPost.created_at)
    order_func = asc if req.order == "asc" else desc

    stmt = stmt.order_by(order_func(sort_field))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar() or 0

    page = max(req.page or 1, 1)
    per_page = min(req.per_page or 10, 100)

    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    items: Sequence[BlogPost] = session.scalars(stmt).all()

    return BlogPostListResponseDTO(
        blogs=[BlogPostResponseDTO.from_model(s) for s in items],
        total=total,
        page=page,
        per_page=per_page,
        sort=req.sort,
        order=req.order,
    )

class GetBlogsByCategory:
    def __init__(self, session: Session, req: PostByCategoryRequestDTO) -> None:
        self.session = session
        self.req = req
    
    def execute(self) -> list[BlogPostResponseDTO]:
        try:
            stmt = (
                select(BlogPost)
                .where(BlogPost.is_published == True, BlogPost.category_id == self.req.category_id)
                .where(BlogPost.slug != self.req.exclude)
                .limit(self.req.per_page)
            )
            items = self.session.scalars(stmt).all()
            return [BlogPostResponseDTO.from_model(s) for s in items]

        except SQLAlchemyError as e:
            raise DatabaseError(f"Database error while fetching posts: {str(e)}")
        
    
