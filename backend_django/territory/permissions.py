"""
Custom permissions for territory app.
"""
from rest_framework import permissions


class IsAdminForWriteOperations(permissions.BasePermission):
    """
    Permission class that:
    - Allows read-only access to all authenticated users
    - Requires superuser/admin for write operations (POST, PUT, PATCH, DELETE)
    """

    def has_permission(self, request, view):
        # Must be authenticated for any access
        if not request.user or not request.user.is_authenticated:
            return False

        # Read operations allowed for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write operations require superuser
        return request.user.is_superuser
