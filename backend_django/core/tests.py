"""
Tests for core app.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Tests for custom User model."""

    def test_create_user(self):
        """Test creating a user with email."""
        user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        assert user.email == 'user@test.com'
        assert user.check_password('testpass123')
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            email='admin@test.com',
            password='adminpass123'
        )
        assert admin.email == 'admin@test.com'
        assert admin.is_staff
        assert admin.is_superuser

    def test_user_str(self):
        """Test user string representation."""
        user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            display_name='Test User'
        )
        assert str(user) == 'Test User'

    def test_user_str_no_display_name(self):
        """Test user string representation without display name."""
        user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        assert str(user) == 'user@test.com'


@pytest.mark.django_db
class TestUserProfileView:
    """Tests for user profile endpoint."""

    def test_get_profile(self, authenticated_client, user):
        """Test getting user profile."""
        response = authenticated_client.get('/api/auth/profile/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    def test_get_profile_unauthenticated(self, api_client):
        """Test getting profile without authentication."""
        response = api_client.get('/api/auth/profile/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile(self, authenticated_client, user):
        """Test updating user profile."""
        response = authenticated_client.patch('/api/auth/profile/', {
            'display_name': 'New Name'
        })
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.display_name == 'New Name'
