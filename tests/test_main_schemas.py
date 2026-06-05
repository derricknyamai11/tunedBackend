"""
Test suite for main blueprint validation schemas.

Tests all Marshmallow schemas used in the main blueprint including:
- NewsletterSubscribeSchema
- SearchQuerySchema
- ServiceFilterSchema
- SampleFilterSchema
- BlogFilterSchema
- BlogCommentSchema
- CommentReactionSchema
"""
import pytest
from marshmallow import ValidationError
from tuned.apis.main.schemas import (
    NewsletterSubscribeSchema,
    SearchQuerySchema,
    ServiceFilterSchema,
    SampleFilterSchema,
    BlogFilterSchema,
    BlogCommentSchema,
    CommentReactionSchema,
)


class TestNewsletterSubscribeSchema:
    """Test NewsletterSubscribeSchema validation"""
    
    def test_valid_email(self):
        """Test that valid email passes validation"""
        schema = NewsletterSubscribeSchema()
        data = {'email': 'test@example.com'}
        result = schema.load(data)
        assert result['email'] == 'test@example.com'
    
    def test_valid_email_with_name(self):
        """Test that valid email with name passes validation"""
        schema = NewsletterSubscribeSchema()
        data = {'email': 'test@example.com', 'name': 'John Doe'}
        result = schema.load(data)
        assert result['email'] == 'test@example.com'
        assert result['name'] == 'John Doe'
    
    def test_invalid_email_format(self):
        """Test that invalid email raises ValidationError"""
        schema = NewsletterSubscribeSchema()
        data = {'email': 'not-an-email'}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'email' in exc_info.value.messages
    
    def test_missing_email(self):
        """Test that missing email raises ValidationError"""
        schema = NewsletterSubscribeSchema()
        data = {}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'email' in exc_info.value.messages
    
    def test_disposable_email_blocked(self):
        """Test that disposable email domains are rejected"""
        schema = NewsletterSubscribeSchema()
        data = {'email': 'test@tempmail.com'}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'disposable' in str(exc_info.value.messages['email'][0]).lower()
    
    def test_name_too_long(self):
        """Test that name exceeding max length raises ValidationError"""
        schema = NewsletterSubscribeSchema()
        data = {
            'email': 'test@example.com',
            'name': 'A' * 101  # Max is 100
        }
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'name' in exc_info.value.messages


class TestSearchQuerySchema:
    """Test SearchQuerySchema validation"""
    
    def test_valid_search_query(self):
        """Test that valid search query passes validation"""
        schema = SearchQuerySchema()
        data = {'q': 'test query'}
        result = schema.load(data)
        assert result['q'] == 'test query'
        assert result['page'] == 1  # Default
        assert result['per_page'] == 20  # Default
    
    def test_search_query_too_short(self):
        """Test that query shorter than 2 chars raises ValidationError"""
        schema = SearchQuerySchema()
        data = {'q': 'a'}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'q' in exc_info.value.messages
    
    def test_search_query_too_long(self):
        """Test that query longer than 200 chars raises ValidationError"""
        schema = SearchQuerySchema()
        data = {'q': 'a' * 201}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'q' in exc_info.value.messages
    
    def test_invalid_search_type(self):
        """Test that invalid type raises ValidationError"""
        schema = SearchQuerySchema()
        data = {'q': 'test', 'type': 'invalid'}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'type' in exc_info.value.messages
    
    def test_valid_search_types(self):
        """Test that all valid types pass validation"""
        schema = SearchQuerySchema()
        valid_types = ['all', 'service', 'sample', 'blog', 'faq', 'tag']
        for search_type in valid_types:
            data = {'q': 'test', 'type': search_type}
            result = schema.load(data)
            assert result['type'] == search_type
    
    def test_pagination_defaults(self):
        """Test that pagination has correct defaults"""
        schema = SearchQuerySchema()
        data = {'q': 'test'}
        result = schema.load(data)
        assert result['page'] == 1
        assert result['per_page'] == 20
    
    def test_custom_pagination(self):
        """Test that custom pagination values work"""
        schema = SearchQuerySchema()
        data = {'q': 'test', 'page': 2, 'per_page': 50}
        result = schema.load(data)
        assert result['page'] == 2
        assert result['per_page'] == 50
    
    def test_per_page_exceeds_max(self):
        """Test that per_page over 100 raises ValidationError"""
        schema = SearchQuerySchema()
        data = {'q': 'test', 'per_page': 101}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'per_page' in exc_info.value.messages


class TestServiceFilterSchema:
    """Test ServiceFilterSchema validation"""
    
    def test_valid_filters(self):
        """Test that valid filters pass validation"""
        schema = ServiceFilterSchema()
        data = {
            'category_id': 1,
            'featured': True,
            'is_active': True,
            'q': 'test',
            'sort': 'name',
            'order': 'asc'
        }
        result = schema.load(data)
        assert result['category_id'] == 1
        assert result['featured'] is True
    
    def test_default_values(self):
        """Test that defaults are applied correctly"""
        schema = ServiceFilterSchema()
        data = {}
        result = schema.load(data)
        assert result['is_active'] is True
        assert result['sort'] == 'name'
        assert result['order'] == 'asc'
        assert result['page'] == 1
        assert result['per_page'] == 20
    
    def test_invalid_sort_field(self):
        """Test that invalid sort field raises ValidationError"""
        schema = ServiceFilterSchema()
        data = {'sort': 'invalid'}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'sort' in exc_info.value.messages
    
    def test_valid_sort_fields(self):
        """Test that all valid sort fields pass"""
        schema = ServiceFilterSchema()
        for sort_field in ['name', 'created_at', 'category']:
            data = {'sort': sort_field}
            result = schema.load(data)
            assert result['sort'] == sort_field


class TestSampleFilterSchema:
    """Test SampleFilterSchema validation"""
    
    def test_valid_filters(self):
        """Test that valid filters pass validation"""
        schema = SampleFilterSchema()
        data = {
            'service_id': 'abc123',
            'featured': True,
            'q': 'test',
            'sort': 'created_at',
            'order': 'desc'
        }
        result = schema.load(data)
        assert result['service_id'] == 'abc123'
        assert result['featured'] is True
    
    def test_default_values(self):
        """Test that defaults are applied correctly"""
        schema = SampleFilterSchema()
        data = {}
        result = schema.load(data)
        assert result['sort'] == 'created_at'
        assert result['order'] == 'desc'
    
    def test_valid_sort_fields(self):
        """Test that all valid sort fields pass"""
        schema = SampleFilterSchema()
        for sort_field in ['created_at', 'word_count', 'title']:
            data = {'sort': sort_field}
            result = schema.load(data)
            assert result['sort'] == sort_field


class TestBlogFilterSchema:
    """Test BlogFilterSchema validation"""
    
    def test_valid_filters(self):
        """Test that valid filters pass validation"""
        schema = BlogFilterSchema()
        data = {
            'category_id': 'abc123',
            'is_published': True,
            'q': 'test',
            'sort': 'published_at',
            'order': 'desc'
        }
        result = schema.load(data)
        assert result['category_id'] == 'abc123'
        assert result['is_published'] is True
    
    def test_default_values(self):
        """Test that defaults are applied correctly"""
        schema = BlogFilterSchema()
        data = {}
        result = schema.load(data)
        assert result['is_published'] is True
        assert result['sort'] == 'published_at'
        assert result['order'] == 'desc'


class TestBlogCommentSchema:
    """Test BlogCommentSchema validation"""
    
    def test_valid_comment(self):
        """Test that valid comment passes validation"""
        schema = BlogCommentSchema()
        data = {'content': 'This is a great post!'}
        result = schema.load(data)
        assert result['content'] == 'This is a great post!'
    
    def test_valid_guest_comment(self):
        """Test that valid guest comment with name/email passes"""
        schema = BlogCommentSchema()
        data = {
            'content': 'Great post!',
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        result = schema.load(data)
        assert result['name'] == 'John Doe'
        assert result['email'] == 'john@example.com'
    
    def test_missing_content(self):
        """Test that missing content raises ValidationError"""
        schema = BlogCommentSchema()
        data = {}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'content' in exc_info.value.messages
    
    def test_content_too_short(self):
        """Test that content shorter than 2 chars raises ValidationError"""
        schema = BlogCommentSchema()
        data = {'content': 'a'}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'content' in exc_info.value.messages
    
    def test_content_too_long(self):
        """Test that content longer than 5000 chars raises ValidationError"""
        schema = BlogCommentSchema()
        data = {'content': 'a' * 5001}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'content' in exc_info.value.messages
    
    def test_spam_detection_excessive_links(self):
        """Test that excessive links trigger spam detection"""
        schema = BlogCommentSchema()
        data = {
            'content': 'Check out http://link1.com and http://link2.com and http://link3.com and http://link4.com'
        }
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'spam' in str(exc_info.value.messages['content'][0]).lower()
    
    def test_spam_detection_repetition(self):
        """Test that excessive repetition triggers spam detection"""
        schema = BlogCommentSchema()
        # Create content with >10 words where one word appears >50% of the time
        data = {
            'content': 'spam ' * 15 + 'word another test'  # 15 'spam' + 3 other words = >50% repetition
        }
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'spam' in str(exc_info.value.messages['content'][0]).lower()


class TestCommentReactionSchema:
    """Test CommentReactionSchema validation"""
    
    def test_valid_like_reaction(self):
        """Test that valid 'like' reaction passes validation"""
        schema = CommentReactionSchema()
        data = {'reaction_type': 'like', 'category_id': 'cat123', 'exclude': 'some-slug'}
        result = schema.load(data)
        assert result['reaction_type'] == 'like'

    def test_valid_dislike_reaction(self):
        """Test that valid 'dislike' reaction passes validation"""
        schema = CommentReactionSchema()
        data = {'reaction_type': 'dislike', 'category_id': 'cat123', 'exclude': 'some-slug'}
        result = schema.load(data)
        assert result['reaction_type'] == 'dislike'
    
    def test_invalid_reaction_type(self):
        """Test that invalid reaction type raises ValidationError"""
        schema = CommentReactionSchema()
        data = {'reaction_type': 'love'}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'reaction_type' in exc_info.value.messages
    
    def test_missing_reaction_type(self):
        """Test that missing reaction type raises ValidationError"""
        schema = CommentReactionSchema()
        data = {}
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        assert 'reaction_type' in exc_info.value.messages
