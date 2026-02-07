"""
Django Admin configuration for core models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from .models import User, RoleAssignment, AuditLog, Gruppo


# =============================================================================
# Unregister Group from auth app and register Gruppo proxy in core
# =============================================================================
admin.site.unregister(Group)


@admin.register(Gruppo)
class GruppoAdmin(BaseGroupAdmin):
    """Gruppo (proxy di Group) sotto l'app core."""
    pass


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


class RoleAssignmentInline(admin.TabularInline):
    """Inline for RoleAssignment in User admin."""
    model = RoleAssignment
    extra = 0
    readonly_fields = ['assigned_at', 'assigned_by_email']
    autocomplete_fields = ['scope_comune', 'scope_provincia', 'scope_regione', 'consultazione']
    fk_name = 'user'


# Add inlines to UserAdmin
UserAdmin.inlines = [RoleAssignmentInline]


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    """Admin configuration for RoleAssignment model."""

    list_display = [
        'user', 'role', 'consultazione', 'scope_type', 'scope_value',
        'is_active', 'assigned_by_email', 'assigned_at'
    ]
    list_filter = ['role', 'consultazione', 'scope_type', 'is_active', 'assigned_at']
    search_fields = ['user__email', 'scope_value', 'notes']
    raw_id_fields = ['user', 'consultazione', 'scope_regione', 'scope_provincia', 'scope_comune']
    readonly_fields = ['assigned_at']

    fieldsets = (
        (None, {
            'fields': ('user', 'role', 'consultazione', 'is_active')
        }),
        (_('Ambito territoriale'), {
            'fields': ('scope_type', 'scope_value', 'scope_regione', 'scope_provincia', 'scope_comune')
        }),
        (_('Validità'), {
            'fields': ('valid_from', 'valid_to')
        }),
        (_('Audit'), {
            'fields': ('assigned_by_email', 'assigned_at', 'notes'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.assigned_by_email = request.user.email
        super().save_model(request, obj, form, change)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for AuditLog model."""

    list_display = ['timestamp', 'user_email', 'action', 'target_model', 'target_id', 'ip_address']
    list_filter = ['action', 'target_model', 'timestamp']
    search_fields = ['user_email', 'target_id', 'ip_address']
    readonly_fields = [
        'user_email', 'action', 'target_model', 'target_id',
        'details', 'ip_address', 'user_agent', 'timestamp'
    ]
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
