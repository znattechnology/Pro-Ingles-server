"""
URL configuration for chat app.
"""

from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Conversations
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/create/', views.ConversationCreateView.as_view(), name='conversation-create'),
    path('conversations/<uuid:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<uuid:conversation_id>/read/', views.mark_conversation_read, name='conversation-read'),
    
    # Messages
    path('conversations/<uuid:conversation_id>/messages/', views.MessageListView.as_view(), name='message-list'),
    path('conversations/<uuid:conversation_id>/messages/create/', views.MessageCreateView.as_view(), name='message-create'),
    path('messages/<uuid:message_id>/report/', views.MessageReportView.as_view(), name='message-report'),
    
    # Notifications
    path('notifications/', views.ChatNotificationListView.as_view(), name='notification-list'),
    
    # Typing indicators
    path('conversations/<uuid:conversation_id>/typing/start/', views.start_typing, name='start-typing'),
    path('conversations/<uuid:conversation_id>/typing/stop/', views.stop_typing, name='stop-typing'),
    path('conversations/<uuid:conversation_id>/typing/update/', views.update_typing_activity, name='update-typing'),
    path('conversations/<uuid:conversation_id>/typing/users/', views.get_typing_users, name='get-typing-users'),
    
    # Search and stats
    path('search/', views.search_conversations, name='search-conversations'),
    path('stats/', views.chat_stats, name='chat-stats'),
    path('typing/cleanup/', views.cleanup_typing_indicators, name='cleanup-typing'),
    path('typing/stats/', views.typing_stats, name='typing-stats'),
]