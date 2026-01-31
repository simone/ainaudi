"""
Django Admin configuration for core models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, IdentityProviderLink, RoleAssignment, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = ['email', 'display_name', 'is_active', 'is_staff', 'last_login']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'created_at']
    search_fields = ['email', 'display_name', 'first_name', 'last_name']
    ordering = ['email']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informazioni personali'), {
            'fields': ('display_name', 'first_name', 'last_name', 'phone_number', 'avatar_url')
        }),
        (_('Permessi'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Date importanti'), {
            'fields': ('last_login', 'created_at', 'last_login_ip'),
        }),
    )
    readonly_fields = ['created_at', 'last_login', 'last_login_ip']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'display_name', 'password1', 'password2'),
        }),
    )


class IdentityProviderLinkInline(admin.TabularInline):
    """Inline for IdentityProviderLink in User admin."""
    model = IdentityProviderLink
    extra = 0
    readonly_fields = ['linked_at', 'last_used_at']


class RoleAssignmentInline(admin.TabularInline):
    """Inline for RoleAssignment in User admin."""
    model = RoleAssignment
    extra = 0
    readonly_fields = ['assigned_at', 'assigned_by']
    fk_name = 'user'


# Add inlines to UserAdmin
UserAdmin.inlines = [IdentityProviderLinkInline, RoleAssignmentInline]


@admin.register(IdentityProviderLink)
class IdentityProviderLinkAdmin(admin.ModelAdmin):
    """Admin configuration for IdentityProviderLink model."""

    list_display = ['user', 'provider', 'provider_email', 'is_primary', 'last_used_at']
    list_filter = ['provider', 'is_primary']
    search_fields = ['user__email', 'provider_email', 'provider_uid']
    raw_id_fields = ['user']
    readonly_fields = ['linked_at', 'last_used_at']


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    """Admin configuration for RoleAssignment model."""

    list_display = [
        'user', 'role', 'scope_type', 'scope_value',
        'is_active', 'assigned_by', 'assigned_at'
    ]
    list_filter = ['role', 'scope_type', 'is_active', 'assigned_at']
    search_fields = ['user__email', 'scope_value', 'notes']
    raw_id_fields = ['user', 'assigned_by', 'scope_regione', 'scope_provincia', 'scope_comune']
    readonly_fields = ['assigned_at']

    fieldsets = (
        (None, {
            'fields': ('user', 'role', 'is_active')
        }),
        (_('Ambito territoriale'), {
            'fields': ('scope_type', 'scope_value', 'scope_regione', 'scope_provincia', 'scope_comune')
        }),
        (_('Validità'), {
            'fields': ('valid_from', 'valid_to')
        }),
        (_('Audit'), {
            'fields': ('assigned_by', 'assigned_at', 'notes'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for AuditLog model."""

    list_display = ['timestamp', 'user', 'action', 'target_model', 'target_id', 'ip_address']
    list_filter = ['action', 'target_model', 'timestamp']
    search_fields = ['user__email', 'target_id', 'ip_address']
    readonly_fields = [
        'user', 'action', 'target_model', 'target_id',
        'details', 'ip_address', 'user_agent', 'timestamp'
    ]
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
