"""
Django admin configuration for chat models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count

from .models import (
    Conversation, Message, ConversationParticipant, MessageReport, ChatNotification
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin interface for Conversation model."""
    
    list_display = [
        'title_display', 'conversation_type', 'participants_count',
        'total_messages', 'last_message_at', 'is_active', 'created_at'
    ]
    list_filter = [
        'conversation_type', 'is_active', 'is_archived', 'created_at'
    ]
    search_fields = ['title', 'participants__email']
    readonly_fields = ['id', 'total_messages', 'last_message_at', 'created_at', 'updated_at']
    filter_horizontal = ['participants']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'conversation_type')
        }),
        ('Participants', {
            'fields': ('participants',)
        }),
        ('Related Objects', {
            'fields': ('booking', 'braider')
        }),
        ('Status', {
            'fields': ('is_active', 'is_archived')
        }),
        ('Statistics', {
            'fields': ('total_messages', 'last_message_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def title_display(self, obj):
        """Display conversation title or auto-generated name."""
        return obj.title if obj.title else str(obj)
    title_display.short_description = "Title"
    
    def participants_count(self, obj):
        """Display number of participants."""
        return obj.participants.count()
    participants_count.short_description = "Participants"
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('participants')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin interface for Message model."""
    
    list_display = [
        'conversation_title', 'sender_email', 'message_preview',
        'message_type', 'is_read', 'is_reported', 'created_at'
    ]
    list_filter = [
        'message_type', 'is_read', 'is_reported', 'is_edited',
        'is_deleted_by_user', 'is_deleted_by_admin', 'created_at'
    ]
    search_fields = ['content', 'sender__email', 'conversation__title']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'attachment_size', 'edited_at'
    ]
    
    fieldsets = (
        ('Message Information', {
            'fields': ('id', 'conversation', 'sender', 'message_type')
        }),
        ('Content', {
            'fields': ('content', 'attachment', 'attachment_name', 'attachment_size')
        }),
        ('Reply', {
            'fields': ('reply_to',)
        }),
        ('Status', {
            'fields': (
                'is_read', 'is_edited', 'edited_at', 'is_reported',
                'is_deleted_by_user', 'is_deleted_by_admin'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['soft_delete_messages', 'restore_messages']
    
    def conversation_title(self, obj):
        """Display conversation title."""
        return obj.conversation.title if obj.conversation.title else f"Conversation {obj.conversation.id}"
    conversation_title.short_description = "Conversation"
    
    def sender_email(self, obj):
        """Display sender email."""
        return obj.sender.email
    sender_email.short_description = "Sender"
    
    def message_preview(self, obj):
        """Display message content preview."""
        if obj.is_deleted:
            return format_html('<em style="color: #999;">Message deleted</em>')
        
        content = obj.content
        if len(content) > 100:
            content = content[:100] + '...'
        
        if obj.attachment:
            content = f"📎 {content}" if content else "📎 Attachment"
        
        return content
    message_preview.short_description = "Content"
    
    def soft_delete_messages(self, request, queryset):
        """Soft delete selected messages."""
        updated = queryset.update(is_deleted_by_admin=True)
        self.message_user(request, f'{updated} messages have been deleted.')
    soft_delete_messages.short_description = "Delete selected messages"
    
    def restore_messages(self, request, queryset):
        """Restore deleted messages."""
        updated = queryset.update(
            is_deleted_by_admin=False,
            is_deleted_by_user=False
        )
        self.message_user(request, f'{updated} messages have been restored.')
    restore_messages.short_description = "Restore selected messages"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'conversation')


@admin.register(MessageReport)
class MessageReportAdmin(admin.ModelAdmin):
    """Admin interface for MessageReport model."""
    
    list_display = [
        'message_preview', 'reporter_email', 'reason_display',
        'status', 'created_at'
    ]
    list_filter = ['reason', 'status', 'created_at']
    search_fields = ['description', 'reporter__email']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('id', 'message', 'reporter')
        }),
        ('Report Details', {
            'fields': ('reason', 'description')
        }),
        ('Moderation', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    actions = ['mark_reviewed', 'mark_resolved']
    
    def message_preview(self, obj):
        """Display reported message preview."""
        content = obj.message.content
        if len(content) > 50:
            content = content[:50] + '...'
        return content
    message_preview.short_description = "Message"
    
    def reporter_email(self, obj):
        """Display reporter email."""
        return obj.reporter.email
    reporter_email.short_description = "Reporter"
    
    def reason_display(self, obj):
        """Display reason with color coding."""
        colors = {
            'inappropriate': '#dc3545',
            'spam': '#fd7e14',
            'harassment': '#dc3545',
            'offensive': '#dc3545',
            'threats': '#dc3545',
            'other': '#6c757d',
        }
        color = colors.get(obj.reason, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_reason_display()
        )
    reason_display.short_description = "Reason"
    
    def mark_reviewed(self, request, queryset):
        """Mark selected reports as reviewed."""
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='reviewed',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} reports have been marked as reviewed.')
    mark_reviewed.short_description = "Mark as reviewed"
    
    def mark_resolved(self, request, queryset):
        """Mark selected reports as resolved."""
        from django.utils import timezone
        updated = queryset.update(
            status='resolved',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} reports have been resolved.')
    mark_resolved.short_description = "Mark as resolved"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'reporter', 'reviewed_by')


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    """Admin interface for ConversationParticipant model."""
    
    list_display = [
        'conversation_title', 'user_email', 'joined_at', 'is_active',
        'notifications_enabled', 'unread_count'
    ]
    list_filter = ['is_active', 'notifications_enabled', 'is_muted', 'joined_at']
    search_fields = ['user__email', 'conversation__title']
    readonly_fields = ['id', 'joined_at', 'unread_count']
    
    def conversation_title(self, obj):
        """Display conversation title."""
        return obj.conversation.title if obj.conversation.title else f"Conversation {obj.conversation.id}"
    conversation_title.short_description = "Conversation"
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = "User"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'conversation')


@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    """Admin interface for ChatNotification model."""
    
    list_display = [
        'user_email', 'notification_type', 'title', 'is_read',
        'is_sent', 'created_at'
    ]
    list_filter = ['notification_type', 'is_read', 'is_sent', 'created_at']
    search_fields = ['user__email', 'title', 'content']
    readonly_fields = ['id', 'created_at']
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = "User"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'conversation')