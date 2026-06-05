from __future__ import annotations
from flask import request
from flask.views import MethodView
from tuned.utils.auth.decorators import combined_auth_check
from flask import g
from tuned.extensions import db
from tuned.utils.responses import success_response, error_response
from typing import Any

class ClientChatList(MethodView):
    decorators = [combined_auth_check(require_admin=False)]
    def get(self) -> tuple[Any, int]:
        from tuned.models.communication import Chat, ChatMessage
        chats = Chat.query.filter_by(user_id=str(g.current_user.id), is_deleted=False).order_by(Chat.updated_at.desc()).all()
        return success_response([{
            'id': str(c.id),
            'subject': getattr(c, 'subject', 'General'),
            'status': c.status.value if hasattr(c.status, 'value') else str(c.status),
            'last_message': ChatMessage.query.filter_by(chat_id=c.id).order_by(ChatMessage.created_at.desc()).first().content if ChatMessage.query.filter_by(chat_id=c.id).first() else None,
            'unread_count': ChatMessage.query.filter_by(chat_id=c.id, is_read=False).count(),
            'updated_at': c.updated_at.isoformat(),
        } for c in chats])
    def post(self) -> tuple[Any, int]:
        from tuned.models.communication import Chat
        data = request.get_json(silent=True) or {}
        chat = Chat(
            user_id=str(g.current_user.id),
            subject=data.get('subject', 'General Inquiry'),
        )
        db.session.add(chat)
        # Add first message if provided
        if data.get('message'):
            from tuned.models.communication import ChatMessage
            db.session.flush()
            msg = ChatMessage(
                chat_id=chat.id,
                user_id=str(g.current_user.id),
                content=data['message'],
                is_read=False,
            )
            db.session.add(msg)
        db.session.commit()
        return success_response({'chat_id': str(chat.id), 'subject': chat.subject}, status=201)

class ClientChatMessages(MethodView):
    decorators = [combined_auth_check(require_admin=False)]
    def get(self, chat_id: str) -> tuple[Any, int]:
        from tuned.models.communication import Chat, ChatMessage
        chat = Chat.query.filter_by(id=chat_id, user_id=str(g.current_user.id), is_deleted=False).first()
        if not chat:
            return error_response('Chat not found', status=404)
        msgs = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at).all()
        # Mark messages as read
        ChatMessage.query.filter_by(chat_id=chat_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return success_response({
            'chat': {'id': str(chat.id), 'subject': getattr(chat, 'subject', 'General'), 'status': chat.status.value if hasattr(chat.status, 'value') else str(chat.status)},
            'messages': [{'id': str(m.id), 'message': m.content, 'user_id': str(m.user_id) if m.user_id else None, 'created_at': m.created_at.isoformat()} for m in msgs],
        })
    def post(self, chat_id: str) -> tuple[Any, int]:
        from tuned.models.communication import Chat, ChatMessage
        chat = Chat.query.filter_by(id=chat_id, user_id=str(g.current_user.id), is_deleted=False).first()
        if not chat:
            return error_response('Chat not found', status=404)
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()
        if not message:
            return error_response('Message is required', status=400)
        msg = ChatMessage(chat_id=chat_id, user_id=str(g.current_user.id), content=message, is_read=False)
        db.session.add(msg)
        db.session.commit()
        return success_response({'id': str(msg.id), 'message': msg.content, 'created_at': msg.created_at.isoformat()}, status=201)
