"""
Core URL configuration for authentication endpoints.
"""
from django.urls import path
from .views import (
    GoogleLoginView,
    MagicLinkRequestView,
    MagicLinkVerifyView,
    UserProfileView,
    UserRolesView,
)

urlpatterns = [
    # Google OAuth
    path('google/', GoogleLoginView.as_view(), name='google_login'),

    # Magic Link
    path('magic-link/request/', MagicLinkRequestView.as_view(), name='magic_link_request'),
    path('magic-link/verify/', MagicLinkVerifyView.as_view(), name='magic_link_verify'),

    # User profile
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('roles/', UserRolesView.as_view(), name='user_roles'),
]
