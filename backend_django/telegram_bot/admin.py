from django.contrib import admin
from .models import TelegramIdentityBinding, TelegramUpdateLog, ExternalChannelConversationLink


@admin.register(TelegramIdentityBinding)
class TelegramIdentityBindingAdmin(admin.ModelAdmin):
    list_display = ('telegram_user_id', 'user', 'binding_status', 'phone_number_normalized', 'first_bound_at', 'last_seen_at')
    list_filter = ('binding_status',)
    search_fields = ('telegram_user_id', 'phone_number_normalized', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)


@admin.register(TelegramUpdateLog)
class TelegramUpdateLogAdmin(admin.ModelAdmin):
    list_display = ('update_id', 'telegram_user_id', 'chat_id', 'update_type', 'processing_status', 'processed_at')
    list_filter = ('processing_status', 'update_type')
    search_fields = ('update_id', 'telegram_user_id')
    readonly_fields = ('processed_at',)


@admin.register(ExternalChannelConversationLink)
class ExternalChannelConversationLinkAdmin(admin.ModelAdmin):
    list_display = ('channel', 'telegram_chat_id', 'telegram_user_id', 'conversation', 'user', 'created_at')
    list_filter = ('channel',)
    search_fields = ('telegram_user_id', 'user__email')
    raw_id_fields = ('conversation', 'user')
