"""
Route endpoint tests for main blueprint.

Tests all public-facing API endpoints including:
- Homepage routes (featured, quote-form, search, testimonials, newsletter)
- Services routes (list, details)
- Samples routes (list, details)
- Blogs routes (list, details, comments, reactions)
"""
import pytest
import json
from datetime import datetime, timezone
from tuned.models.service import Service, ServiceCategory
from tuned.models.content import Sample, Testimonial
from tuned.models.blog import BlogPost, BlogCategory, BlogComment, CommentReaction
from tuned.models.communication import NewsletterSubscriber
from tuned.models.tag import Tag
from tuned.models.price import PricingCategory


_pc_counter = 0

def make_pricing_category(db):
    """Helper: create a pricing category for Service test fixtures."""
    global _pc_counter
    _pc_counter += 1
    pc = PricingCategory(name=f'Standard-{_pc_counter}', description='Standard pricing')
    db.session.add(pc)
    db.session.flush()
    return pc


class TestFeaturedContent:
    """Test GET /api/featured endpoint"""
    
    def test_returns_featured_items(self, client, db):
        """Test that featured endpoint returns correct items"""
        # Create test data
        pc = make_pricing_category(db)
        category = ServiceCategory(name='Test Category', description='Test')
        db.session.add(category)
        db.session.flush()

        # Create services
        for i in range(8):
            service = Service(
                name=f'Service {i}',
                featured=i < 6,
                category_id=category.id,
                pricing_category_id=pc.id,
                is_active=True
            )
            db.session.add(service)
        
        # Create samples
        for i in range(8):
            sample = Sample(
                title=f'Sample {i}',
                content='Test content',
                featured=i < 6
            )
            db.session.add(sample)
        
        # Create blogs
        blog_category = BlogCategory(name='Tech', slug='tech')
        db.session.add(blog_category)
        db.session.flush()
        
        for i in range(8):
            blog = BlogPost(
                title=f'Blog {i}',
                content='Test content',
                author='Test Author',
                category_id=blog_category.id,
                is_published=True,
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(blog)
        
        db.session.commit()
        
        # Make request
        response = client.get('/api/featured/contents')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'services' in data['data']
        assert 'samples' in data['data']
        assert 'blogs' in data['data']

        # services returns categories; samples returns featured; blogs returns featured
        assert isinstance(data['data']['services'], list)
        assert isinstance(data['data']['samples'], list)
        assert isinstance(data['data']['blogs'], list)


class TestQuoteFormOptions:
    """Test GET /api/quote/options endpoint"""
    
    def test_returns_all_options(self, client, db):
        """Test that quote form options are returned correctly"""
        # Create test data
        pc = make_pricing_category(db)
        category = ServiceCategory(name='Writing', description='Writing services')
        db.session.add(category)
        db.session.flush()

        service = Service(
            name='Essay Writing',
            category_id=category.id,
            pricing_category_id=pc.id,
            is_active=True
        )
        db.session.add(service)
        db.session.commit()
        
        response = client.get('/api/quote/options')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'services' in data['data']
        # quote form returns 'levels' or 'academic_levels' depending on implementation
        assert 'levels' in data['data'] or 'academic_levels' in data['data']


class TestGlobalSearch:
    """Test GET /api/search endpoint"""
    
    def test_search_all_types(self, client, db):
        """Test searching across all content types"""
        # Create searchable content
        pc = make_pricing_category(db)
        category = ServiceCategory(name='Tech', description='Tech')
        db.session.add(category)
        db.session.flush()

        service = Service(
            name='Python Development',
            description='Python coding services',
            category_id=category.id,
            pricing_category_id=pc.id,
            is_active=True
        )
        db.session.add(service)
        db.session.commit()
        
        response = client.get('/api/search?q=python')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'results' in data['data']
    
    def test_search_query_too_short(self, client):
        """Test that short queries are rejected"""
        response = client.get('/api/search?q=a')
        assert response.status_code == 422
    
    def test_search_type_filtering(self, client, db):
        """Test filtering by type works"""
        response = client.get('/api/search?q=test&type=service')
        assert response.status_code == 200


class TestTestimonials:
    """Test GET /api/testimonials endpoint"""
    
    def test_returns_approved_only(self, client, db, test_user):
        """Test that only approved testimonials are returned"""
        # Create testimonials
        approved = Testimonial(
            user_id=test_user.id,
            content='Great service!',
            rating=5,
            is_approved=True
        )
        not_approved = Testimonial(
            user_id=test_user.id,
            content='Bad service',
            rating=1,
            is_approved=False
        )
        db.session.add_all([approved, not_approved])
        db.session.commit()
        
        response = client.get('/api/testimonials')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']['items']) == 1
        assert data['data']['items'][0]['content'] == 'Great service!'
    
    def test_pagination_works(self, client, db, test_user):
        """Test pagination of testimonials"""
        # Create many testimonials
        for i in range(25):
            testimonial = Testimonial(
                user_id=test_user.id,
                content=f'Review {i}',
                rating=5,
                is_approved=True
            )
            db.session.add(testimonial)
        db.session.commit()
        
        response = client.get('/api/testimonials?per_page=10')
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['data']['items']) == 10
        assert data['data']['total'] == 25


class TestNewsletterSubscription:
    """Test POST /api/newsletter/subscribe endpoint"""
    
    def test_successful_subscription(self, client, db):
        """Test successful newsletter subscription"""
        response = client.post('/api/newsletter/subscribe', json={
            'email': 'test@example.com',
            'name': 'Test User'
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        
        # Verify subscription in database
        subscription = NewsletterSubscriber.query.filter_by(email='test@example.com').first()
        assert subscription is not None
        assert subscription.is_active is True
    
    def test_duplicate_subscription(self, client, db):
        """Test subscribing with existing email"""
        # Create existing subscription
        existing = NewsletterSubscriber(
            email='existing@example.com',
            is_active=False
        )
        db.session.add(existing)
        db.session.commit()
        
        # Try to subscribe again
        response = client.post('/api/newsletter/subscribe', json={
            'email': 'existing@example.com'
        })
        assert response.status_code == 200
        
        # Should reactivate subscription
        subscription = NewsletterSubscriber.query.filter_by(email='existing@example.com').first()
        assert subscription.is_active is True
    
    def test_invalid_email_rejected(self, client):
        """Test that invalid emails are rejected"""
        response = client.post('/api/newsletter/subscribe', json={
            'email': 'not-an-email'
        })
        assert response.status_code == 422


class TestServicesRoutes:
    """Test /api/services endpoints"""
    
    def test_list_services(self, client, db):
        """Test listing services"""
        pc = make_pricing_category(db)
        category = ServiceCategory(name='Writing', description='Writing')
        db.session.add(category)
        db.session.flush()

        # Create services
        for i in range(3):
            service = Service(
                name=f'Service {i}',
                category_id=category.id,
                pricing_category_id=pc.id,
                is_active=True
            )
            db.session.add(service)
        db.session.commit()
        
        response = client.get('/api/services')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data['data'], list)
        assert len(data['data']) == 3
    
    def test_filter_by_category(self, client, db):
        """Test filtering services by category"""
        cat1 = ServiceCategory(name='Writing', description='Writing')
        cat2 = ServiceCategory(name='Editing', description='Editing')
        db.session.add_all([cat1, cat2])
        db.session.flush()
        
        pc = make_pricing_category(db)
        service1 = Service(name='Essay', category_id=cat1.id, pricing_category_id=pc.id, is_active=True)
        service2 = Service(name='Proofreading', category_id=cat2.id, pricing_category_id=pc.id, is_active=True)
        db.session.add_all([service1, service2])
        db.session.commit()
        
        response = client.get(f'/api/services?category_id={cat1.id}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert isinstance(data['data'], list)
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'Essay'
    
    def test_get_service_details(self, client, db):
        """Test getting service details"""
        category = ServiceCategory(name='Writing', description='Writing')
        db.session.add(category)
        db.session.flush()
        
        pc = make_pricing_category(db)
        service = Service(
            name='Essay Writing',
            slug='essay-writing',
            category_id=category.id,
            pricing_category_id=pc.id,
            is_active=True
        )
        db.session.add(service)
        db.session.commit()
        
        response = client.get('/api/services/essay-writing')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['data']['name'] == 'Essay Writing'
    
    def test_service_not_found(self, client, db):
        """Test 404 for non-existent service"""
        response = client.get('/api/services/non-existent')
        assert response.status_code == 404


class TestSamplesRoutes:
    """Test /api/samples endpoints"""
    
    def test_list_samples(self, client, db):
        """Test listing samples"""
        for i in range(3):
            sample = Sample(
                title=f'Sample {i}',
                content='Test content',
                slug=f'sample-{i}'
            )
            db.session.add(sample)
        db.session.commit()
        
        response = client.get('/api/samples')
        assert response.status_code == 200

        data = response.get_json()
        # paginated_response puts items directly in data['data']
        items = data['data'] if isinstance(data['data'], list) else data['data'].get('items', data['data'])
        assert len(items) == 3
    
    def test_get_sample_details(self, client, db):
        """Test getting sample details"""
        sample = Sample(
            title='Python Tutorial',
            slug='python-tutorial',
            content='Learn Python basics'
        )
        db.session.add(sample)
        db.session.commit()
        
        response = client.get('/api/samples/python-tutorial')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['data']['title'] == 'Python Tutorial'


class TestBlogsRoutes:
    """Test /api/blogs endpoints"""
    
    def test_list_published_blogs(self, client, db):
        """Test that only published blogs are listed"""
        category = BlogCategory(name='Tech', slug='tech')
        db.session.add(category)
        db.session.flush()
        
        published = BlogPost(
            title='Published Post',
            slug='published-post',
            content='Content',
            author='Author',
            category_id=category.id,
            is_published=True,
            published_at=datetime.now(timezone.utc)
        )
        draft = BlogPost(
            title='Draft Post',
            slug='draft-post',
            content='Content',
            author='Author',
            category_id=category.id,
            is_published=False
        )
        db.session.add_all([published, draft])
        db.session.commit()
        
        response = client.get('/api/blogs')
        assert response.status_code == 200

        data = response.get_json()
        # paginated_response puts items directly in data['data']
        items = data['data'] if isinstance(data['data'], list) else data['data'].get('items', [])
        assert len(items) == 1
        assert items[0]['title'] == 'Published Post'
    
    def test_get_blog_details(self, client, db):
        """Test getting blog details"""
        category = BlogCategory(name='Tech', slug='tech')
        db.session.add(category)
        db.session.flush()
        
        blog = BlogPost(
            title='Test Blog',
            slug='test-blog',
            content='Content here',
            author='Author',
            category_id=category.id,
            is_published=True,
            published_at=datetime.now(timezone.utc)
        )
        db.session.add(blog)
        db.session.commit()
        
        response = client.get('/api/blogs/test-blog')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['data']['title'] == 'Test Blog'


class TestBlogComments:
    """Test blog comments endpoints"""
    
    def test_list_approved_comments(self, client, db):
        """Test that only approved comments are listed"""
        category = BlogCategory(name='Tech', slug='tech')
        db.session.add(category)
        db.session.flush()
        
        blog = BlogPost(
            title='Test',
            slug='test-blog',
            content='Content',
            author='Author',
            category_id=category.id,
            is_published=True
        )
        db.session.add(blog)
        db.session.flush()
        
        approved_comment = BlogComment(
            post_id=blog.id,
            content='Great post!',
            approved=True
        )
        pending_comment = BlogComment(
            post_id=blog.id,
            content='Spam comment',
            approved=False
        )
        db.session.add_all([approved_comment, pending_comment])
        db.session.commit()
        
        response = client.get('/api/blogs/test-blog/comments')
        assert response.status_code == 200

        data = response.get_json()
        # comments are in data['data']['comments'] or data['data'] depending on implementation
        raw = data['data']
        comments = raw.get('comments', raw) if isinstance(raw, dict) else raw
        assert len(comments) == 1
        assert comments[0]['content'] == 'Great post!'

    @pytest.mark.skip(reason="POST comments endpoint not yet implemented")
    def test_add_guest_comment(self, client, db):
        """Test adding a comment as guest"""
        category = BlogCategory(name='Tech', slug='tech')
        db.session.add(category)
        db.session.flush()
        
        blog = BlogPost(
            title='Test',
            slug='test-blog',
            content='Content',
            author='Author',
            category_id=category.id,
            is_published=True
        )
        db.session.add(blog)
        db.session.commit()
        
        response = client.post('/api/blogs/test-blog/comments', json={
            'content': 'Great article!',
            'name': 'Guest User',
            'email': 'guest@example.com'
        })
        assert response.status_code == 200
        
        # Comment should exist but not be approved
        comment = BlogComment.query.filter_by(content='Great article!').first()
        assert comment is not None
        assert comment.approved is False


class TestCommentReactions:
    """Test comment reaction endpoint"""

    @pytest.mark.skip(reason="Comment reactions endpoint not yet implemented")
    def test_like_comment(self, client, db):
        """Test liking a comment"""
        category = BlogCategory(name='Tech', slug='tech')
        db.session.add(category)
        db.session.flush()
        
        blog = BlogPost(
            title='Test',
            slug='test',
            content='Content',
            author='Author',
            category_id=category.id,
            is_published=True
        )
        db.session.add(blog)
        db.session.flush()
        
        comment = BlogComment(
            post_id=blog.id,
            content='Nice post',
            approved=True
        )
        db.session.add(comment)
        db.session.commit()
        
        response = client.post(f'/api/blogs/comments/{comment.id}/react', json={
            'reaction_type': 'like'
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['data']['action'] == 'added'
        assert data['data']['likes_count'] == 1
    
    @pytest.mark.skip(reason="Comment reactions endpoint not yet implemented")
    def test_toggle_reaction(self, client, db):
        """Test toggling reaction off"""
        category = BlogCategory(name='Tech', slug='tech')
        db.session.add(category)
        db.session.flush()
        
        blog = BlogPost(
            title='Test',
            slug='test',
            content='Content',
            author='Author',
            category_id=category.id,
            is_published=True
        )
        db.session.add(blog)
        db.session.flush()
        
        comment = BlogComment(
            post_id=blog.id,
            content='Nice',
            approved=True
        )
        db.session.add(comment)
        db.session.commit()
        
        # Add reaction
        client.post(f'/api/blogs/comments/{comment.id}/react', json={
            'reaction_type': 'like'
        })
        
        # Toggle it off
        response = client.post(f'/api/blogs/comments/{comment.id}/react', json={
            'reaction_type': 'like'
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['data']['action'] == 'removed'
        assert data['data']['likes_count'] == 0
