from datetime import datetime, timezone
from typing import Any

from flask import g, request
from flask.views import MethodView

from tuned.extensions import db
from tuned.models.content import Testimonial
from tuned.utils.auth.decorators import combined_auth_check
from tuned.utils.responses import success_response, error_response


class ClientTestimonialSubmit(MethodView):
    decorators = [combined_auth_check(require_admin=False)]

    def post(self) -> tuple[Any, int]:
        data = request.get_json() or {}
        content = (data.get("content") or "").strip()
        rating = int(data.get("rating", 5))

        if not content or len(content) < 10:
            return error_response("Review must be at least 10 characters", 400)
        if not (1 <= rating <= 5):
            return error_response("Rating must be between 1 and 5", 400)

        testimonial = Testimonial(
            content=content,
            rating=rating,
            is_approved=False,
            user_id=str(g.current_user.id),
        )
        db.session.add(testimonial)
        db.session.commit()

        return success_response({
            "id": testimonial.id,
            "message": "Thank you! Your review has been submitted and is pending approval.",
        }, 201)
