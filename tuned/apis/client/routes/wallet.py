from __future__ import annotations
import os
from flask import request
from flask.views import MethodView
from tuned.utils.auth.decorators import combined_auth_check
from flask import g
from tuned.extensions import db
from tuned.utils.responses import success_response, error_response
from typing import Any

class WalletView(MethodView):
    decorators = [combined_auth_check(require_admin=False)]
    def get(self) -> tuple[Any, int]:
        return success_response({
            'balance': float(getattr(current_user, 'wallet_balance', 0.0)),
            'reward_points': g.current_user.reward_points,
            'currency': 'USD',
        })

class WalletTopup(MethodView):
    decorators = [combined_auth_check(require_admin=False)]
    def post(self) -> tuple[Any, int]:
        data = request.get_json(silent=True) or {}
        amount = float(data.get('amount', 0))
        if amount < 5:
            return error_response('Minimum topup amount is $5.00', status=400)
        stripe_key = os.environ.get('STRIPE_SECRET_KEY', '')
        if stripe_key and stripe_key != 'sk_test_placeholder':
            try:
                import stripe
                stripe.api_key = stripe_key
                intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),
                    currency='usd',
                    metadata={'user_id': str(g.current_user.id), 'type': 'wallet_topup'},
                )
                return success_response({'client_secret': intent.client_secret, 'amount': amount, 'stripe_enabled': True})
            except Exception as e:
                return error_response(f'Payment gateway error: {str(e)}', status=500)
        # Dev mode: no Stripe key — return mock
        return success_response({
            'client_secret': f'pi_mock_{g.current_user.id}_secret',
            'amount': amount,
            'stripe_enabled': False,
            'note': 'Add STRIPE_SECRET_KEY to .env for real payments',
        })

class WalletConfirm(MethodView):
    """Called by frontend after Stripe payment succeeds"""
    decorators = [combined_auth_check(require_admin=False)]
    def post(self) -> tuple[Any, int]:
        data = request.get_json(silent=True) or {}
        amount = float(data.get('amount', 0))
        if amount <= 0:
            return error_response('Invalid amount', status=400)
        g.current_user.wallet_balance = float(getattr(current_user, 'wallet_balance', 0)) + amount
        db.session.commit()
        return success_response({
            'balance': float(g.current_user.wallet_balance),
            'added': amount,
            'message': f'${amount:.2f} added to your wallet',
        })

class WalletDeduct(MethodView):
    """Internal: deduct from wallet when paying for order"""
    decorators = [combined_auth_check(require_admin=False)]
    def post(self) -> tuple[Any, int]:
        data = request.get_json(silent=True) or {}
        amount = float(data.get('amount', 0))
        if amount <= 0:
            return error_response('Invalid amount', status=400)
        balance = float(getattr(current_user, 'wallet_balance', 0))
        if balance < amount:
            return error_response(f'Insufficient balance. You have ${balance:.2f}', status=400)
        g.current_user.wallet_balance = balance - amount
        db.session.commit()
        return success_response({'balance': float(g.current_user.wallet_balance), 'deducted': amount})
