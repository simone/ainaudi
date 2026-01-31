"""
Pytest configuration and fixtures for Django tests.
"""
import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user(db):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        display_name='Test User'
    )


@pytest.fixture
def admin_user(db):
    """Create a test admin user."""
    User = get_user_model()
    return User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123',
        display_name='Admin User'
    )


@pytest.fixture
def api_client():
    """Create a test API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Create an authenticated test API client."""
    api_client.force_authenticate(user=user)
    return api_client
