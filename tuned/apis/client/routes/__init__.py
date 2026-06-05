from tuned.apis.client.routes.dashboard import (
    NavStats,
    DashboardKPIs,
    DashboardAnalytics,
    DashboardTracking,
    DashboardAlerts
)
from tuned.apis.client.routes.orders import ReorderOrder
from tuned.apis.client.routes.profile import (
    ProfileView,
    AvatarUploadView,
    VerifyEmailView,
    ChangePasswordView
)
from tuned.apis.client.routes.settings import SettingsView, SettingsCategoryView
from tuned.apis.client.routes.referrals import (
    ReferralListView,
    ReferralStatsView,
    ReferralShareView,
    ReferralRedeemView
)
from tuned.apis.client.routes.wallet import WalletView, WalletTopup, WalletConfirm, WalletDeduct
from tuned.apis.client.routes.chat import ClientChatList, ClientChatMessages
from tuned.apis.client.routes.testimonial import ClientTestimonialSubmit


from typing import Any

CLIENT_ROUTES: list[dict[str, Any]] = [
    {
        "rule": "/nav-stats",
        "view_func": NavStats.as_view("client_nav_stats"),
        "methods": ["GET"],
    },
    {
        "rule": "/dashboard/kpis",
        "view_func": DashboardKPIs.as_view("dashboard_kpis"),
        "methods": ["GET"],
    },
    {
        "rule": "/dashboard/analytics",
        "view_func": DashboardAnalytics.as_view("dashboard_analytics"),
        "methods": ["GET"],
    },
    {
        "rule": "/dashboard/tracking",
        "view_func": DashboardTracking.as_view("dashboard_tracking"),
        "methods": ["GET"],
    },
    {
        "rule": "/dashboard/alerts",
        "view_func": DashboardAlerts.as_view("dashboard_alerts"),
        "methods": ["GET"],
    },
    {
        "rule": "/orders/<string:order_id>/reorder",
        "view_func": ReorderOrder.as_view("order_reorder"),
        "methods": ["POST"],
    },
    {
        "rule": "/profile",
        "view_func": ProfileView.as_view("profile_view"),
        "methods": ["GET", "PATCH"],
    },
    {
        "rule": "/profile/avatar",
        "view_func": AvatarUploadView.as_view("avatar_upload_view"),
        "methods": ["POST", "DELETE"],
    },
    {
        "rule": "/profile/verify-email",
        "view_func": VerifyEmailView.as_view("verify_email_view"),
        "methods": ["POST"],
    },
    {
        "rule": "/profile/change-password",
        "view_func": ChangePasswordView.as_view("change_password_view"),
        "methods": ["POST"],
    },
    {
        "rule": "/settings",
        "view_func": SettingsView.as_view("settings_view"),
        "methods": ["GET"],
    },
    {
        "rule": "/settings/<string:category>",
        "view_func": SettingsCategoryView.as_view("settings_category_view"),
        "methods": ["PATCH"],
    },
    {
        "rule": "/referrals",
        "view_func": ReferralListView.as_view("referral_list_view"),
        "methods": ["GET"],
    },
    {
        "rule": "/referrals/stats",
        "view_func": ReferralStatsView.as_view("referral_stats_view"),
        "methods": ["GET"],
    },
    {
        "rule": "/referrals/share",
        "view_func": ReferralShareView.as_view("referral_share_view"),
        "methods": ["POST"],
    },
    {
        "rule": "/referrals/redeem",
        "view_func": ReferralRedeemView.as_view("referral_redeem_view"),
        "methods": ["POST"],
    },
    # Wallet
    {'rule': '/wallet', 'view_func': WalletView.as_view('wallet_view'), 'methods': ['GET']},
    {'rule': '/wallet/topup', 'view_func': WalletTopup.as_view('wallet_topup'), 'methods': ['POST']},
    {'rule': '/wallet/confirm', 'view_func': WalletConfirm.as_view('wallet_confirm'), 'methods': ['POST']},
    {'rule': '/wallet/deduct', 'view_func': WalletDeduct.as_view('wallet_deduct'), 'methods': ['POST']},
    # Chat
    {'rule': '/chat', 'view_func': ClientChatList.as_view('client_chat_list'), 'methods': ['GET', 'POST']},
    {'rule': '/chat/<string:chat_id>/messages', 'view_func': ClientChatMessages.as_view('client_chat_messages'), 'methods': ['GET', 'POST']},
    # Testimonial submission
    {'rule': '/testimonials', 'view_func': ClientTestimonialSubmit.as_view('client_testimonial_submit'), 'methods': ['POST']},
]
