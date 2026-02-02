"""
Core URL configuration for authentication endpoints.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import (
    GoogleLoginView,
    MagicLinkRequestView,
    MagicLinkVerifyView,
    UserProfileView,
    UserRolesView,
    ImpersonateView,
    SearchUsersView,
)

urlpatterns = [
    # Google OAuth
    path('google/', GoogleLoginView.as_view(), name='google_login'),

    # Magic Link
    path('magic-link/request/', MagicLinkRequestView.as_view(), name='magic_link_request'),
    path('magic-link/verify/', MagicLinkVerifyView.as_view(), name='magic_link_verify'),

    # JWT Token management
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # User profile
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('roles/', UserRolesView.as_view(), name='user_roles'),

    # Impersonation (superuser only)
    path('impersonate/', ImpersonateView.as_view(), name='impersonate'),

    # Search users (superuser only)
    path('users/search/', SearchUsersView.as_view(), name='search_users'),
]
