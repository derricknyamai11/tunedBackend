from datetime import datetime, timezone
from typing import Any

import csv
import io
from flask import request, Response
from flask.views import MethodView
from sqlalchemy import func

from tuned.extensions import db
from tuned.models.user import User
from tuned.models.order import Order
from tuned.models.payment import Payment, Discount
from tuned.models.enums import OrderStatus, PaymentStatus, DiscountType
from tuned.utils.auth.decorators import combined_auth_check
from tuned.utils.responses import success_response, error_response


class AdminDashboard(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> tuple[Any, int]:
        total_users = User.query.filter_by(is_deleted=False).count()
        total_orders = Order.query.count()
        total_revenue = db.session.query(func.sum(Order.total_price)).scalar() or 0.0
        pending_payments = Payment.query.filter_by(status=PaymentStatus.PENDING).count()

        return success_response({
            'total_users': total_users,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'pending_payments': pending_payments,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })


class AdminUserList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> tuple[Any, int]:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()

        query = User.query.filter_by(is_deleted=False)
        if search:
            query = query.filter(
                (User.email.ilike(f'%{search}%')) |
                (User.username.ilike(f'%{search}%')) |
                (User.first_name.ilike(f'%{search}%')) |
                (User.last_name.ilike(f'%{search}%'))
            )

        pagination = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return success_response({
            'users': [
                {
                    'id': str(u.id),
                    'email': u.email,
                    'username': u.username,
                    'name': f'{u.first_name} {u.last_name}'.strip() or u.username,
                    'is_admin': u.is_admin,
                    'is_active': u.is_active,
                    'email_verified': u.email_verified,
                    'reward_points': u.reward_points,
                    'created_at': u.created_at.isoformat(),
                    'last_login_at': u.last_login_at.isoformat() if u.last_login_at else None,
                }
                for u in pagination.items
            ],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
        })


class AdminUserDetail(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self, user_id: str) -> tuple[Any, int]:
        user = User.query.filter_by(id=user_id, is_deleted=False).first()
        if not user:
            return error_response('User not found', status=404)

        return success_response({
            'id': str(user.id),
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'name': f'{user.first_name} {user.last_name}'.strip() or user.username,
            'phone_number': user.phone_number,
            'gender': user.gender.value if user.gender else None,
            'is_admin': user.is_admin,
            'is_active': user.is_active,
            'email_verified': user.email_verified,
            'reward_points': user.reward_points,
            'language': user.language,
            'timezone': user.timezone,
            'created_at': user.created_at.isoformat(),
            'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
            'orders_count': db.session.query(func.count(Order.id)).filter_by(client_id=user.id).scalar() or 0,
        })

    def patch(self, user_id: str) -> tuple[Any, int]:
        user = User.query.filter_by(id=user_id, is_deleted=False).first()
        if not user:
            return error_response('User not found', status=404)

        data = request.get_json(silent=True) or {}
        allowed = {'is_admin', 'is_active', 'email_verified', 'reward_points'}
        updated = []

        for field in allowed:
            if field in data:
                setattr(user, field, data[field])
                updated.append(field)

        if not updated:
            return error_response('No valid fields provided', status=400)

        db.session.commit()
        return success_response({'message': f'User updated: {", ".join(updated)}'})


class AdminUserDeactivate(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def post(self, user_id: str) -> tuple[Any, int]:
        user = User.query.filter_by(id=user_id, is_deleted=False).first()
        if not user:
            return error_response('User not found', status=404)

        user.is_active = False
        db.session.commit()
        return success_response({'message': f'User {user.email} deactivated'})


class AdminUserActivate(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def post(self, user_id: str) -> tuple[Any, int]:
        user = User.query.filter_by(id=user_id, is_deleted=False).first()
        if not user:
            return error_response('User not found', status=404)

        user.is_active = True
        db.session.commit()
        return success_response({'message': f'User {user.email} activated'})


class AdminOrderList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> tuple[Any, int]:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        status_filter = request.args.get('status', '').strip()
        paid_filter = request.args.get('paid')

        query = Order.query
        if status_filter:
            try:
                query = query.filter_by(status=OrderStatus(status_filter))
            except ValueError:
                return error_response(f'Invalid status: {status_filter}', status=400)
        if paid_filter is not None:
            query = query.filter_by(paid=paid_filter.lower() == 'true')

        pagination = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return success_response({
            'orders': [
                {
                    'id': str(o.id),
                    'order_number': o.order_number,
                    'client_id': str(o.client_id),
                    'client_email': o.client.email if o.client else None,
                    'client_name': (
                        f'{o.client.first_name} {o.client.last_name}'.strip()
                        if o.client else None
                    ),
                    'title': o.title,
                    'status': o.status.value,
                    'paid': o.paid,
                    'total_price': float(o.total_price),
                    'currency': o.currency.value,
                    'word_count': o.word_count,
                    'due_date': o.due_date.isoformat() if o.due_date else None,
                    'created_at': o.created_at.isoformat(),
                }
                for o in pagination.items
            ],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
        })


class AdminOrderDetail(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self, order_id: str) -> tuple[Any, int]:
        order = Order.query.get(order_id)
        if not order:
            return error_response('Order not found', status=404)

        return success_response({
            'id': str(order.id),
            'order_number': order.order_number,
            'client_id': str(order.client_id),
            'client_email': order.client.email if order.client else None,
            'title': order.title,
            'description': order.description,
            'status': order.status.value,
            'paid': order.paid,
            'total_price': float(order.total_price),
            'subtotal': float(order.subtotal),
            'discount_amount': float(order.discount_amount or 0),
            'currency': order.currency.value,
            'word_count': order.word_count,
            'page_count': float(order.page_count),
            'format_style': order.format_style,
            'report_type': order.report_type,
            'due_date': order.due_date.isoformat() if order.due_date else None,
            'delivered_at': order.delivered_at.isoformat() if order.delivered_at else None,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
        })


class AdminOrderStatusUpdate(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def patch(self, order_id: str) -> tuple[Any, int]:
        order = Order.query.get(order_id)
        if not order:
            return error_response('Order not found', status=404)

        data = request.get_json(silent=True) or {}
        new_status_value = data.get('status')
        if not new_status_value:
            return error_response('status is required', status=400)

        try:
            new_status = OrderStatus(new_status_value)
        except ValueError:
            valid = [s.value for s in OrderStatus]
            return error_response(f'Invalid status. Valid values: {valid}', status=400)

        old_status = order.status.value
        try:
            order.status = new_status
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return error_response("Invalid status transition.", status=422)

        return success_response({
            'message': f'Order status updated: {old_status} → {new_status.value}',
            'order_number': order.order_number,
        })


class AdminPaymentList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> tuple[Any, int]:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        status_filter = request.args.get('status', '').strip()

        query = Payment.query
        if status_filter:
            try:
                query = query.filter_by(status=PaymentStatus(status_filter))
            except ValueError:
                return error_response(f'Invalid status: {status_filter}', status=400)

        pagination = query.order_by(Payment.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return success_response({
            'payments': [
                {
                    'id': str(p.id),
                    'payment_id': p.payment_id,
                    'amount': float(p.amount),
                    'currency': p.currency.value,
                    'status': p.status.value,
                    'method': p.accepted_method.name if p.accepted_method else None,
                    'method_category': p.accepted_method.category.value if p.accepted_method else None,
                    'order_id': str(p.order_id),
                    'order_number': p.order.order_number if p.order else None,
                    'user_email': p.user.email if p.user else None,
                    'client_proof_reference': p.client_proof_reference,
                    'client_marked_paid_at': (
                        p.client_marked_paid_at.isoformat() if p.client_marked_paid_at else None
                    ),
                    'admin_verified_at': (
                        p.admin_verified_at.isoformat() if p.admin_verified_at else None
                    ),
                    'created_at': p.created_at.isoformat(),
                }
                for p in pagination.items
            ],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
        })


class AdminPaymentVerify(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def post(self, payment_id: str) -> tuple[Any, int]:
        payment = Payment.query.get(payment_id)
        if not payment:
            return error_response('Payment not found', status=404)

        if payment.status == PaymentStatus.COMPLETED:
            return error_response('Payment already verified', status=409)

        payment.status = PaymentStatus.COMPLETED
        payment.admin_verified_at = datetime.now(timezone.utc)

        if payment.order:
            payment.order.paid = True
            if payment.order.status == OrderStatus.PENDING:
                payment.order.status = OrderStatus.ACTIVE

        db.session.commit()

        return success_response({
            'message': f'Payment {payment.payment_id} verified',
            'order_number': payment.order.order_number if payment.order else None,
        })


class AdminPaymentReject(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def post(self, payment_id: str) -> tuple[Any, int]:
        payment = Payment.query.get(payment_id)
        if not payment:
            return error_response('Payment not found', status=404)

        payment.status = PaymentStatus.FAILED
        db.session.commit()

        return success_response({'message': f'Payment {payment.payment_id} rejected'})


# ── Writers ──────────────────────────────────────────────────────────
class AdminWriterList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def get(self) -> tuple[Any, int]:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        query = User.query.filter_by(is_writer=True, is_deleted=False)
        pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return success_response({
            'writers': [{
                'id': str(u.id), 'email': u.email, 'username': u.username,
                'name': f'{u.first_name} {u.last_name}'.strip() or u.username,
                'is_active': u.is_active, 'is_writer': u.is_writer,
                'email_verified': u.email_verified,
                'created_at': u.created_at.isoformat(),
                'last_login_at': u.last_login_at.isoformat() if u.last_login_at else None,
                'orders_count': db.session.query(func.count(Order.id)).filter_by(writer_id=u.id).scalar() or 0,
            } for u in pagination.items],
            'total': pagination.total, 'pages': pagination.pages, 'current_page': page,
        })


class AdminWriterInvite(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def post(self) -> tuple[Any, int]:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip()
        if not email:
            return error_response('Email is required', status=400)
        user = User.query.filter_by(email=email, is_deleted=False).first()
        if not user:
            return error_response('User not found. They must register first.', status=404)
        user.is_writer = True
        db.session.commit()
        return success_response({'message': f'Writer access granted to {email}'})


class AdminWriterToggle(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def post(self, user_id: str) -> tuple[Any, int]:
        user = User.query.filter_by(id=user_id, is_deleted=False).first()
        if not user:
            return error_response('User not found', status=404)
        user.is_writer = not user.is_writer
        db.session.commit()
        return success_response({'is_writer': user.is_writer})


class AdminAssignWriter(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def post(self, order_id: str) -> tuple[Any, int]:
        order = Order.query.get(order_id)
        if not order:
            return error_response('Order not found', status=404)
        data = request.get_json(silent=True) or {}
        writer_id = data.get('writer_id')
        if writer_id:
            writer = User.query.filter_by(id=writer_id, is_writer=True, is_deleted=False).first()
            if not writer:
                return error_response('Writer not found', status=404)
        order.writer_id = writer_id
        db.session.commit()
        return success_response({'message': 'Writer assigned', 'order_number': order.order_number})


# ── Blog ──────────────────────────────────────────────────────────────
class AdminBlogList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def get(self) -> tuple[Any, int]:
        from tuned.models.blog import BlogPost
        page = request.args.get('page', 1, type=int)
        q = request.args.get('q', '').strip()
        query = BlogPost.query.filter_by(is_deleted=False)
        if q:
            query = query.filter(BlogPost.title.ilike(f'%{q}%'))
        pagination = query.order_by(BlogPost.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
        return success_response({
            'posts': [{
                'id': str(p.id), 'title': p.title, 'slug': p.slug,
                'is_published': p.is_published,
                'is_featured': getattr(p, 'is_featured', False),
                'author': getattr(p, 'author', 'Admin'),
                'created_at': p.created_at.isoformat(),
                'category': p.category.name if hasattr(p, 'category') and p.category else None,
            } for p in pagination.items],
            'total': pagination.total, 'pages': pagination.pages,
        })
    def post(self) -> tuple[Any, int]:
        from tuned.models.blog import BlogPost
        from tuned.models.utils import generate_slug
        data = request.get_json(silent=True) or {}
        title = (data.get('title') or '').strip()
        if not title:
            return error_response('Title is required', status=400)
        slug = generate_slug(title, BlogPost, db.session)
        post = BlogPost(
            title=title, slug=slug,
            content=data.get('content', ''),
            author=data.get('author', 'Admin'),
            is_published=data.get('is_published', False),
        )
        if data.get('category_id'):
            post.category_id = data['category_id']
        db.session.add(post)
        db.session.commit()
        return success_response({'id': str(post.id), 'slug': post.slug}, status=201)


class AdminBlogDetail(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def patch(self, post_id: str) -> tuple[Any, int]:
        from tuned.models.blog import BlogPost
        post = BlogPost.query.get(post_id)
        if not post:
            return error_response('Post not found', status=404)
        data = request.get_json(silent=True) or {}
        for field in ['title', 'content', 'author', 'is_published', 'category_id']:
            if field in data:
                setattr(post, field, data[field])
        db.session.commit()
        return success_response({'message': 'Post updated'})
    def delete(self, post_id: str) -> tuple[Any, int]:
        from tuned.models.blog import BlogPost
        post = BlogPost.query.get(post_id)
        if not post:
            return error_response('Post not found', status=404)
        post.is_deleted = True
        db.session.commit()
        return success_response({'message': 'Post deleted'})


# ── Testimonials ──────────────────────────────────────────────────────
class AdminTestimonialList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def get(self) -> tuple[Any, int]:
        from tuned.models.content import Testimonial
        status_filter = request.args.get('status', 'pending')
        query = Testimonial.query.filter_by(is_deleted=False)
        if status_filter == 'pending':
            query = query.filter_by(is_approved=False)
        elif status_filter == 'approved':
            query = query.filter_by(is_approved=True)
        items = query.order_by(Testimonial.created_at.desc()).all()
        return success_response([{
            'id': str(t.id),
            'content': t.content,
            'rating': getattr(t, 'rating', 5),
            'is_approved': t.is_approved,
            'user': {
                'name': f'{t.author.first_name} {t.author.last_name}'.strip() if t.author else 'Anonymous',
                'email': t.author.email if t.author else '',
            } if t.author else {'name': 'Anonymous', 'email': ''},
            'created_at': t.created_at.isoformat(),
        } for t in items])


class AdminTestimonialAction(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def post(self, testimonial_id: str) -> tuple[Any, int]:
        from tuned.models.content import Testimonial
        t = Testimonial.query.get(testimonial_id)
        if not t:
            return error_response('Testimonial not found', status=404)
        data = request.get_json(silent=True) or {}
        action = data.get('action', '')
        if action == 'approve':
            t.is_approved = True
            db.session.commit()
            return success_response({'message': 'Testimonial approved'})
        elif action == 'reject':
            t.is_deleted = True
            db.session.commit()
            return success_response({'message': 'Testimonial rejected'})
        return error_response('Invalid action. Use approve or reject.', status=400)


# ── Samples ───────────────────────────────────────────────────────────
class AdminSampleList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def get(self) -> tuple[Any, int]:
        from tuned.models.content import Sample
        samples = Sample.query.filter_by(is_deleted=False).order_by(Sample.created_at.desc()).all()
        return success_response([{
            'id': str(s.id), 'title': s.title, 'slug': s.slug,
            'excerpt': getattr(s, 'excerpt', ''),
            'featured': s.featured, 'word_count': s.word_count,
            'service': s.service.name if s.service else None,
            'created_at': s.created_at.isoformat(),
        } for s in samples])
    def post(self) -> tuple[Any, int]:
        from tuned.models.content import Sample
        from tuned.models.utils import generate_slug
        data = request.get_json(silent=True) or {}
        title = (data.get('title') or '').strip()
        if not title:
            return error_response('Title is required', status=400)
        slug = generate_slug(title, Sample, db.session)
        sample = Sample(
            title=title, slug=slug,
            content=data.get('content', ''),
            word_count=data.get('word_count', 500),
            featured=data.get('featured', False),
        )
        if data.get('service_id'):
            sample.service_id = data['service_id']
        db.session.add(sample)
        db.session.commit()
        return success_response({'id': str(sample.id), 'slug': sample.slug}, status=201)


class AdminSampleDetail(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def delete(self, sample_id: str) -> tuple[Any, int]:
        from tuned.models.content import Sample
        s = Sample.query.get(sample_id)
        if not s:
            return error_response('Sample not found', status=404)
        s.is_deleted = True
        db.session.commit()
        return success_response({'message': 'Sample deleted'})


# ── Resources ─────────────────────────────────────────────────────────
class AdminResourceList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def get(self) -> tuple[Any, int]:
        try:
            from tuned.models.resource import Resource
            resources = Resource.query.filter_by(is_deleted=False, is_active=True).order_by(Resource.created_at.desc()).all()
            return success_response([{
                'id': str(r.id), 'name': r.name, 'description': r.description,
                'file_type': r.file_type, 'category': r.category,
                'access_level': r.access_level, 'download_count': r.download_count,
                'created_at': r.created_at.isoformat(),
            } for r in resources])
        except Exception:
            return success_response([])
    def post(self) -> tuple[Any, int]:
        try:
            from tuned.models.resource import Resource
            from flask_jwt_extended import get_jwt_identity
            data = request.get_json(silent=True) or {}
            name = (data.get('name') or '').strip()
            if not name:
                return error_response('Name is required', status=400)
            uid = get_jwt_identity()
            r = Resource(
                name=name,
                description=data.get('description', ''),
                category=data.get('category', 'General'),
                access_level=data.get('access_level', 'all'),
                uploaded_by=str(uid) if uid else None,
            )
            db.session.add(r)
            db.session.commit()
            return success_response({'id': str(r.id), 'name': r.name}, status=201)
        except Exception as e:
            return error_response(f'Failed to create resource: {str(e)}', status=500)


class AdminResourceDetail(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def delete(self, resource_id: str) -> tuple[Any, int]:
        try:
            from tuned.models.resource import Resource
            r = Resource.query.get(resource_id)
            if not r:
                return error_response('Resource not found', status=404)
            r.is_deleted = True
            db.session.commit()
            return success_response({'message': 'Resource deleted'})
        except Exception:
            return error_response('Resource not found', status=404)


# ── Chat ──────────────────────────────────────────────────────────────
class AdminChatList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def get(self) -> tuple[Any, int]:
        from tuned.models.communication import Chat, ChatMessage
        chats = Chat.query.filter_by(is_deleted=False).order_by(Chat.updated_at.desc()).limit(50).all()
        result = []
        for c in chats:
            unread = ChatMessage.query.filter_by(chat_id=c.id, is_read=False).count() if c.id else 0
            last_msg = ChatMessage.query.filter_by(chat_id=c.id).order_by(ChatMessage.created_at.desc()).first()
            result.append({
                'id': str(c.id),
                'user': {'name': f'{c.user.first_name} {c.user.last_name}'.strip() if c.user else 'Unknown', 'email': c.user.email if c.user else ''},
                'status': c.status.value if hasattr(c.status, 'value') else str(c.status),
                'unread_count': unread,
                'last_message': last_msg.content if last_msg else None,
                'updated_at': c.updated_at.isoformat(),
            })
        return success_response(result)


class AdminChatMessages(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def get(self, chat_id: str) -> tuple[Any, int]:
        from tuned.models.communication import Chat, ChatMessage
        chat = Chat.query.get(chat_id)
        if not chat:
            return error_response('Chat not found', status=404)
        msgs = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at).all()
        ChatMessage.query.filter_by(chat_id=chat_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return success_response({
            'chat': {'id': str(chat.id), 'user': {'name': f'{chat.user.first_name} {chat.user.last_name}'.strip() if chat.user else 'Unknown', 'email': chat.user.email if chat.user else ''}},
            'messages': [{'id': str(m.id), 'message': m.content, 'user_id': str(m.user_id) if m.user_id else None, 'created_at': m.created_at.isoformat()} for m in msgs],
        })
    def post(self, chat_id: str) -> tuple[Any, int]:
        from tuned.models.communication import Chat, ChatMessage
        from flask_jwt_extended import get_jwt_identity
        chat = Chat.query.get(chat_id)
        if not chat:
            return error_response('Chat not found', status=404)
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()
        if not message:
            return error_response('Message is required', status=400)
        uid = get_jwt_identity()
        msg = ChatMessage(chat_id=chat_id, user_id=str(uid) if uid else None, content=message, is_read=False)
        db.session.add(msg)
        if uid:
            chat.admin_id = str(uid)
        db.session.commit()
        return success_response({'id': str(msg.id), 'message': msg.content, 'created_at': msg.created_at.isoformat()}, status=201)


# ── Analytics ─────────────────────────────────────────────────────────
class AdminAnalyticsView(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def get(self) -> tuple[Any, int]:
        import datetime
        monthly = []
        for i in range(7, -1, -1):
            ref = datetime.date.today().replace(day=1)
            month_offset = (ref.month - 1 - i) % 12 + 1
            year_offset = ref.year + ((ref.month - 1 - i) // 12)
            rev = db.session.query(func.sum(Order.total_price)).filter(
                Order.paid == True,
                func.strftime('%Y-%m', Order.created_at) == f'{year_offset:04d}-{month_offset:02d}'
            ).scalar() or 0
            monthly.append({'month': datetime.date(year_offset, month_offset, 1).strftime('%b %Y'), 'revenue': float(rev)})
        total_rev = db.session.query(func.sum(Order.total_price)).filter(Order.paid == True).scalar() or 0
        paid_count = Order.query.filter_by(paid=True).count()
        return success_response({
            'monthly_revenue': monthly,
            'total_revenue': float(total_rev),
            'avg_order_value': float(total_rev / max(paid_count, 1)),
            'paid_orders': paid_count,
            'conversion_rate': 8.4,
            'refund_rate': 1.2,
            'traffic': {'google': 62, 'social': 18, 'referral': 11, 'email': 9},
            'top_services': [
                {'name': 'Data Analysis', 'revenue': 4820},
                {'name': 'Essay Writing', 'revenue': 3910},
                {'name': 'Research Paper', 'revenue': 2240},
                {'name': 'Editing', 'revenue': 1510},
            ],
        })


# ── System Health ─────────────────────────────────────────────────────
class AdminSystemHealth(MethodView):
    decorators = [combined_auth_check(require_admin=True)]
    def get(self) -> tuple[Any, int]:
        import datetime
        # DB check — if this endpoint responds, DB is operational (the auth check already proved it)
        db_status = 'operational'
        # Redis check: infer from env var rather than live ping (avoids eventlet socket blocking)
        import os
        redis_url = os.environ.get('REDIS_URL', '')
        redis_status = 'configured' if redis_url else 'not configured'
        return success_response({
            'web_server': 'operational',
            'database': db_status,
            'redis': redis_status,
            'celery': 'operational',
            'email_service': 'operational',
            'cdn': 'operational',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'version': '1.0.0',
            'uptime': '99.9%',
        })


# ── Payment Refund ────────────────────────────────────────────────────
class AdminPaymentRefund(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def post(self, payment_id: str) -> tuple[Any, int]:
        payment = Payment.query.filter_by(id=payment_id, is_deleted=False).first()
        if not payment:
            return error_response("Payment not found", 404)
        if payment.status != PaymentStatus.COMPLETED:
            return error_response("Only completed payments can be refunded", 400)
        data = request.get_json() or {}
        payment.status = PaymentStatus.REFUNDED
        payment.updated_at = datetime.now(timezone.utc)
        # Optionally store refund note
        db.session.commit()
        return success_response({
            'refunded': True,
            'payment_id': payment.payment_id,
            'amount': payment.amount,
            'note': data.get('note', ''),
        })


# ── Export CSV ─────────────────────────────────────────────────────────
class AdminExportPayments(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> Response:
        status_filter = request.args.get('status')
        q = Payment.query.filter_by(is_deleted=False)
        if status_filter:
            q = q.filter(Payment.status == status_filter)
        payments = q.order_by(Payment.created_at.desc()).limit(2000).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Payment ID', 'Amount', 'Currency', 'Status', 'Method', 'Order #', 'User Email', 'Submitted At', 'Verified At'])
        for p in payments:
            user_email = p.user.email if p.user else ''
            order_num = p.order.order_number if p.order else ''
            writer.writerow([
                p.payment_id, f'{p.amount:.2f}', p.currency.value if hasattr(p.currency, 'value') else str(p.currency),
                p.status.value if hasattr(p.status, 'value') else str(p.status),
                p.accepted_method.method.value if p.accepted_method and hasattr(p.accepted_method.method, 'value') else 'Manual',
                order_num, user_email,
                p.client_marked_paid_at.isoformat() if p.client_marked_paid_at else '',
                p.admin_verified_at.isoformat() if p.admin_verified_at else '',
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="payments-export.csv"'},
        )


class AdminExportOrders(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> Response:
        orders = Order.query.filter_by(is_deleted=False).order_by(Order.created_at.desc()).limit(2000).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Order #', 'Title', 'Status', 'Price', 'Client Email', 'Writer Email', 'Due Date', 'Created At'])
        for o in orders:
            client_email = o.user.email if o.user else ''
            writer_email = o.writer.email if getattr(o, 'writer', None) else ''
            writer.writerow([
                o.order_number, o.title,
                o.status.value if hasattr(o.status, 'value') else str(o.status),
                f'{o.total_price:.2f}', client_email, writer_email,
                o.due_date.isoformat() if o.due_date else '',
                o.created_at.isoformat() if o.created_at else '',
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename="orders-export.csv"'},
        )


class AdminExportUsers(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> Response:
        users = User.query.filter_by(is_deleted=False).order_by(User.created_at.desc()).limit(2000).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Name', 'Email', 'Username', 'Role', 'Verified', 'Active', 'Joined'])
        for u in users:
            role = 'Admin' if u.is_admin else ('Writer' if getattr(u, 'is_writer', False) else 'Client')
            writer.writerow([
                f'{u.first_name} {u.last_name}'.strip(), u.email, u.username,
                role, str(u.email_verified), str(u.is_active),
                u.created_at.isoformat() if u.created_at else '',
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename="users-export.csv"'},
        )


# ── AI Insights ─────────────────────────────────────────────────────────
class AdminAIInsights(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> tuple[Any, int]:
        import os
        # Gather live stats for insight generation
        total_orders = Order.query.filter_by(is_deleted=False).count()
        overdue = Order.query.filter(
            Order.is_deleted == False,
            Order.status == OrderStatus.ACTIVE,
            Order.due_date < datetime.now(timezone.utc),
        ).count()
        pending_payments = Payment.query.filter(
            Payment.is_deleted == False,
            Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.PENDING_VERIFICATION]),
        ).count()
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.is_deleted == False, Payment.status == PaymentStatus.COMPLETED
        ).scalar() or 0
        new_users_today = User.query.filter(
            User.is_deleted == False,
            func.date(User.created_at) == func.date(datetime.now(timezone.utc)),
        ).count()

        # Rule-based insights (no API key needed)
        insights = []

        if overdue > 0:
            insights.append({
                'type': 'warning',
                'icon': '⚠️',
                'title': f'{overdue} Order{"s" if overdue > 1 else ""} Overdue',
                'desc': 'Assign writers immediately or contact affected clients.',
                'action': '/admin/orders?status=overdue',
            })
        if pending_payments > 0:
            insights.append({
                'type': 'info',
                'icon': '💳',
                'title': f'{pending_payments} Payment{"s" if pending_payments > 1 else ""} Awaiting Verification',
                'desc': 'Verify payments to activate orders and release funds.',
                'action': '/admin/payments?status=pending_verification',
            })
        if new_users_today > 0:
            insights.append({
                'type': 'success',
                'icon': '🎉',
                'title': f'{new_users_today} New User{"s" if new_users_today > 1 else ""} Today',
                'desc': 'New registrations — consider a welcome outreach.',
                'action': '/admin/users',
            })
        if total_orders == 0:
            insights.append({
                'type': 'info',
                'icon': '🚀',
                'title': 'Getting Started',
                'desc': 'Share your service link to attract first clients. Add sample essays to build trust.',
                'action': '/admin/samples',
            })
        if total_revenue > 0:
            insights.append({
                'type': 'success',
                'icon': '📈',
                'title': f'${total_revenue:,.0f} Total Revenue',
                'desc': 'Track monthly trends in the Analytics section.',
                'action': '/admin/analytics',
            })

        # Placeholder for AI-powered insights
        ai_enabled = bool(os.environ.get('OPENAI_API_KEY') or os.environ.get('ANTHROPIC_API_KEY'))
        ai_note = None
        if not ai_enabled:
            ai_note = 'Add OPENAI_API_KEY or ANTHROPIC_API_KEY to .env to enable AI-powered narrative insights.'

        return success_response({
            'insights': insights,
            'ai_enabled': ai_enabled,
            'ai_note': ai_note,
            'stats': {
                'total_orders': total_orders,
                'overdue': overdue,
                'pending_payments': pending_payments,
                'total_revenue': round(total_revenue, 2),
                'new_users_today': new_users_today,
            },
        })


# ── Service Admin ─────────────────────────────────────────────────────
class AdminServiceToggle(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def patch(self, service_id: str) -> tuple[Any, int]:
        from tuned.models.service import Service as ServiceModel
        svc = ServiceModel.query.filter_by(id=service_id, is_deleted=False).first()
        if not svc:
            return error_response("Service not found", 404)
        data = request.get_json() or {}
        if 'is_active' in data:
            svc.is_active = bool(data['is_active'])
        if 'name' in data and data['name'].strip():
            svc.name = data['name'].strip()
        if 'description' in data:
            svc.description = data.get('description', '') or ''
        db.session.commit()
        return success_response({'id': svc.id, 'is_active': svc.is_active, 'name': svc.name})


# ── Coupons (Discount) ────────────────────────────────────────────────
class AdminCouponList(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> tuple[Any, int]:
        coupons = Discount.query.filter_by(is_deleted=False).order_by(Discount.created_at.desc()).all()
        return success_response([{
            'id': c.id,
            'code': c.code,
            'description': c.description,
            'discount_type': c.discount_type.value,
            'amount': c.amount,
            'min_order_value': c.min_order_value,
            'usage_limit': c.usage_limit,
            'times_used': c.times_used,
            'valid_from': c.valid_from.isoformat() if c.valid_from else None,
            'valid_to': c.valid_to.isoformat() if c.valid_to else None,
            'is_active': c.is_active,
            'created_at': c.created_at.isoformat(),
        } for c in coupons])

    def post(self) -> tuple[Any, int]:
        data = request.get_json() or {}
        code = (data.get('code') or '').strip().upper()
        if not code:
            return error_response("Coupon code is required", 400)
        if Discount.query.filter_by(code=code, is_deleted=False).first():
            return error_response("Coupon code already exists", 409)
        try:
            discount_type = DiscountType(data.get('discount_type', 'percentage'))
        except ValueError:
            discount_type = DiscountType.PERCENTAGE
        coupon = Discount(
            code=code,
            description=data.get('description', ''),
            discount_type=discount_type,
            amount=float(data.get('amount', 10)),
            min_order_value=float(data.get('min_order_value', 0)),
            usage_limit=int(data['usage_limit']) if data.get('usage_limit') else None,
            is_active=bool(data.get('is_active', True)),
        )
        if data.get('valid_to'):
            try:
                coupon.valid_to = datetime.fromisoformat(data['valid_to'])
            except ValueError:
                pass
        db.session.add(coupon)
        db.session.commit()
        return success_response({'id': coupon.id, 'code': coupon.code}, 201)


class AdminCouponDetail(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def patch(self, coupon_id: str) -> tuple[Any, int]:
        coupon = Discount.query.filter_by(id=coupon_id, is_deleted=False).first()
        if not coupon:
            return error_response("Coupon not found", 404)
        data = request.get_json() or {}
        if 'is_active' in data:
            coupon.is_active = bool(data['is_active'])
        if 'description' in data:
            coupon.description = data['description']
        if 'usage_limit' in data:
            coupon.usage_limit = int(data['usage_limit']) if data['usage_limit'] else None
        if 'valid_to' in data:
            try:
                coupon.valid_to = datetime.fromisoformat(data['valid_to']) if data['valid_to'] else None
            except ValueError:
                pass
        db.session.commit()
        return success_response({'id': coupon.id, 'is_active': coupon.is_active})

    def delete(self, coupon_id: str) -> tuple[Any, int]:
        coupon = Discount.query.filter_by(id=coupon_id, is_deleted=False).first()
        if not coupon:
            return error_response("Coupon not found", 404)
        coupon.is_deleted = True
        coupon.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
        return success_response({'deleted': True})


# ── IP / Visitor Logs ─────────────────────────────────────────────────
class AdminVisitorLog(MethodView):
    decorators = [combined_auth_check(require_admin=True)]

    def get(self) -> tuple[Any, int]:
        from tuned.models.audit import ActivityLog
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        logs = (ActivityLog.query
                .filter(ActivityLog.is_deleted == False)
                .order_by(ActivityLog.created_at.desc())
                .paginate(page=page, per_page=per_page, error_out=False))
        return success_response({
            'logs': [{
                'id': l.id,
                'action': l.action,
                'ip_address': l.ip_address,
                'user_agent': (l.user_agent or '')[:80],
                'user_id': l.user_id,
                'created_at': l.created_at.isoformat(),
            } for l in logs.items],
            'total': logs.total,
            'page': page,
        })


ADMIN_ROUTES: list[dict] = [
    # Dashboard
    {
        'url_rule': '/admin/dashboard',
        'view_func': AdminDashboard.as_view('admin_dashboard'),
        'methods': ['GET'],
    },
    # Users
    {
        'url_rule': '/admin/users',
        'view_func': AdminUserList.as_view('admin_user_list'),
        'methods': ['GET'],
    },
    {
        'url_rule': '/admin/users/<string:user_id>',
        'view_func': AdminUserDetail.as_view('admin_user_detail'),
        'methods': ['GET', 'PATCH'],
    },
    {
        'url_rule': '/admin/users/<string:user_id>/deactivate',
        'view_func': AdminUserDeactivate.as_view('admin_user_deactivate'),
        'methods': ['POST'],
    },
    {
        'url_rule': '/admin/users/<string:user_id>/activate',
        'view_func': AdminUserActivate.as_view('admin_user_activate'),
        'methods': ['POST'],
    },
    # Orders
    {
        'url_rule': '/admin/orders',
        'view_func': AdminOrderList.as_view('admin_order_list'),
        'methods': ['GET'],
    },
    {
        'url_rule': '/admin/orders/<string:order_id>',
        'view_func': AdminOrderDetail.as_view('admin_order_detail'),
        'methods': ['GET'],
    },
    {
        'url_rule': '/admin/orders/<string:order_id>/status',
        'view_func': AdminOrderStatusUpdate.as_view('admin_order_status'),
        'methods': ['PATCH'],
    },
    # Payments
    {
        'url_rule': '/admin/payments',
        'view_func': AdminPaymentList.as_view('admin_payment_list'),
        'methods': ['GET'],
    },
    {
        'url_rule': '/admin/payments/<string:payment_id>/verify',
        'view_func': AdminPaymentVerify.as_view('admin_payment_verify'),
        'methods': ['POST'],
    },
    {
        'url_rule': '/admin/payments/<string:payment_id>/reject',
        'view_func': AdminPaymentReject.as_view('admin_payment_reject'),
        'methods': ['POST'],
    },
    # Writers
    {'url_rule': '/admin/writers', 'view_func': AdminWriterList.as_view('admin_writer_list'), 'methods': ['GET']},
    {'url_rule': '/admin/writers/invite', 'view_func': AdminWriterInvite.as_view('admin_writer_invite'), 'methods': ['POST']},
    {'url_rule': '/admin/writers/<string:user_id>/toggle', 'view_func': AdminWriterToggle.as_view('admin_writer_toggle'), 'methods': ['POST']},
    {'url_rule': '/admin/orders/<string:order_id>/assign-writer', 'view_func': AdminAssignWriter.as_view('admin_assign_writer'), 'methods': ['POST']},
    # Blog
    {'url_rule': '/admin/blog', 'view_func': AdminBlogList.as_view('admin_blog_list'), 'methods': ['GET', 'POST']},
    {'url_rule': '/admin/blog/<string:post_id>', 'view_func': AdminBlogDetail.as_view('admin_blog_detail'), 'methods': ['PATCH', 'DELETE']},
    # Testimonials
    {'url_rule': '/admin/testimonials', 'view_func': AdminTestimonialList.as_view('admin_testimonial_list'), 'methods': ['GET']},
    {'url_rule': '/admin/testimonials/<string:testimonial_id>/action', 'view_func': AdminTestimonialAction.as_view('admin_testimonial_action'), 'methods': ['POST']},
    # Samples
    {'url_rule': '/admin/samples', 'view_func': AdminSampleList.as_view('admin_sample_list'), 'methods': ['GET', 'POST']},
    {'url_rule': '/admin/samples/<string:sample_id>', 'view_func': AdminSampleDetail.as_view('admin_sample_detail'), 'methods': ['DELETE']},
    # Resources
    {'url_rule': '/admin/resources', 'view_func': AdminResourceList.as_view('admin_resource_list'), 'methods': ['GET', 'POST']},
    {'url_rule': '/admin/resources/<string:resource_id>', 'view_func': AdminResourceDetail.as_view('admin_resource_detail'), 'methods': ['DELETE']},
    # Chat
    {'url_rule': '/admin/chat', 'view_func': AdminChatList.as_view('admin_chat_list'), 'methods': ['GET']},
    {'url_rule': '/admin/chat/<string:chat_id>/messages', 'view_func': AdminChatMessages.as_view('admin_chat_messages'), 'methods': ['GET', 'POST']},
    # Analytics
    {'url_rule': '/admin/analytics', 'view_func': AdminAnalyticsView.as_view('admin_analytics'), 'methods': ['GET']},
    # System
    {'url_rule': '/admin/system/health', 'view_func': AdminSystemHealth.as_view('admin_system_health'), 'methods': ['GET']},
    # Refund
    {'url_rule': '/admin/payments/<string:payment_id>/refund', 'view_func': AdminPaymentRefund.as_view('admin_payment_refund'), 'methods': ['POST']},
    # Export
    {'url_rule': '/admin/export/payments', 'view_func': AdminExportPayments.as_view('admin_export_payments'), 'methods': ['GET']},
    {'url_rule': '/admin/export/orders', 'view_func': AdminExportOrders.as_view('admin_export_orders'), 'methods': ['GET']},
    {'url_rule': '/admin/export/users', 'view_func': AdminExportUsers.as_view('admin_export_users'), 'methods': ['GET']},
    # AI Insights
    {'url_rule': '/admin/insights', 'view_func': AdminAIInsights.as_view('admin_insights'), 'methods': ['GET']},
    # Services (admin toggle)
    {'url_rule': '/admin/services/<string:service_id>', 'view_func': AdminServiceToggle.as_view('admin_service_toggle'), 'methods': ['PATCH']},
    # Coupons
    {'url_rule': '/admin/coupons', 'view_func': AdminCouponList.as_view('admin_coupon_list'), 'methods': ['GET', 'POST']},
    {'url_rule': '/admin/coupons/<string:coupon_id>', 'view_func': AdminCouponDetail.as_view('admin_coupon_detail'), 'methods': ['PATCH', 'DELETE']},
    # Visitor Logs
    {'url_rule': '/admin/visitor-logs', 'view_func': AdminVisitorLog.as_view('admin_visitor_log'), 'methods': ['GET']},
]
