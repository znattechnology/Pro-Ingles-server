"""
Django admin configuration for ratings and reviews.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg
from django.utils import timezone

from .models import (
    BraiderReview, ProductReview, ReviewImage, ReviewHelpfulness,
    ReviewResponse, ReviewReport
)


class ReviewImageInline(admin.TabularInline):
    """Inline admin for review images."""
    model = ReviewImage
    extra = 0
    fields = ['image_preview', 'image', 'caption', 'image_type', 'sort_order']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 120px;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Preview"


@admin.register(BraiderReview)
class BraiderReviewAdmin(admin.ModelAdmin):
    """Admin interface for BraiderReview model."""
    
    list_display = [
        'braider_name', 'user_email', 'overall_rating_stars', 'title',
        'status_badge', 'is_verified', 'helpfulness_score',
        'would_recommend_icon', 'created_at'
    ]
    list_filter = [
        'status', 'is_verified', 'would_recommend', 'overall_rating',
        'created_at', 'braider__name'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'braider__name', 'title', 'comment'
    ]
    readonly_fields = [
        'id', 'user', 'braider', 'booking', 'created_at', 'updated_at',
        'helpfulness_score', 'average_detailed_rating'
    ]
    
    fieldsets = (
        ('Review Information', {
            'fields': (
                'id', 'user', 'braider', 'booking', 'is_verified'
            )
        }),
        ('Ratings', {
            'fields': (
                'overall_rating', 'quality_rating', 'professionalism_rating',
                'communication_rating', 'value_rating', 'average_detailed_rating'
            )
        }),
        ('Review Content', {
            'fields': (
                'title', 'comment', 'would_recommend'
            )
        }),
        ('Moderation', {
            'fields': (
                'status', 'moderation_notes', 'moderated_by', 'moderated_at'
            )
        }),
        ('Helpfulness', {
            'fields': (
                'helpful_count', 'not_helpful_count', 'helpfulness_score'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ReviewImageInline]
    
    actions = ['approve_reviews', 'reject_reviews', 'flag_reviews']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'braider', 'booking__service', 'moderated_by'
        )
    
    def braider_name(self, obj):
        """Display braider name with link."""
        url = reverse('admin:braiders_braider_change', args=[obj.braider.id])
        return format_html('<a href="{}">{}</a>', url, obj.braider.name)
    braider_name.short_description = "Braider"
    
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = "User"
    
    def overall_rating_stars(self, obj):
        """Display rating as stars."""
        stars = '★' * int(obj.overall_rating) + '☆' * (5 - int(obj.overall_rating))
        return format_html(
            '<span style="color: #ffc107; font-size: 16px;">{}</span> ({})',
            stars, obj.overall_rating
        )
    overall_rating_stars.short_description = "Rating"
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'flagged': '#fd7e14',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def would_recommend_icon(self, obj):
        """Display recommendation as icon."""
        if obj.would_recommend:
            return format_html('<span style="color: green; font-size: 16px;">👍</span>')
        return format_html('<span style="color: red; font-size: 16px;">👎</span>')
    would_recommend_icon.short_description = "Recommend"
    
    def helpfulness_score(self, obj):
        """Display helpfulness score."""
        total_votes = obj.helpful_count + obj.not_helpful_count
        if total_votes == 0:
            return "No votes"
        
        helpful_percentage = (obj.helpful_count / total_votes) * 100
        color = "#28a745" if helpful_percentage >= 70 else "#ffc107" if helpful_percentage >= 40 else "#dc3545"
        
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color,
            obj.helpful_count,
            total_votes,
            round(helpful_percentage, 1)
        )
    helpfulness_score.short_description = "Helpful Score"
    
    # Admin actions
    def approve_reviews(self, request, queryset):
        """Approve selected reviews."""
        updated = queryset.filter(status='pending').update(
            status='approved',
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(request, f'{updated} reviews have been approved.')
    approve_reviews.short_description = "Approve selected reviews"
    
    def reject_reviews(self, request, queryset):
        """Reject selected reviews."""
        updated = queryset.filter(status='pending').update(
            status='rejected',
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(request, f'{updated} reviews have been rejected.')
    reject_reviews.short_description = "Reject selected reviews"
    
    def flag_reviews(self, request, queryset):
        """Flag selected reviews for further review."""
        updated = queryset.update(
            status='flagged',
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(request, f'{updated} reviews have been flagged.')
    flag_reviews.short_description = "Flag selected reviews"


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """Admin interface for ProductReview model."""
    
    list_display = [
        'product_name', 'user_email', 'rating_stars', 'title',
        'status_badge', 'is_verified_purchase', 'helpfulness_score',
        'would_recommend_icon', 'created_at'
    ]
    list_filter = [
        'status', 'is_verified_purchase', 'would_recommend', 'rating',
        'created_at', 'product__category'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'product__name', 'title', 'comment'
    ]
    readonly_fields = [
        'id', 'user', 'product', 'order', 'created_at', 'updated_at',
        'helpfulness_score'
    ]
    
    fieldsets = (
        ('Review Information', {
            'fields': (
                'id', 'user', 'product', 'order', 'is_verified_purchase'
            )
        }),
        ('Ratings', {
            'fields': (
                'rating', 'quality_rating', 'value_rating'
            )
        }),
        ('Review Content', {
            'fields': (
                'title', 'comment', 'would_recommend'
            )
        }),
        ('Moderation', {
            'fields': (
                'status', 'moderation_notes', 'moderated_by', 'moderated_at'
            )
        }),
        ('Helpfulness', {
            'fields': (
                'helpful_count', 'not_helpful_count', 'helpfulness_score'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ReviewImageInline]
    
    actions = ['approve_reviews', 'reject_reviews', 'flag_reviews']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'product', 'order', 'moderated_by'
        )
    
    def product_name(self, obj):
        """Display product name with link."""
        url = reverse('admin:ecommerce_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_name.short_description = "Product"
    
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = "User"
    
    def rating_stars(self, obj):
        """Display rating as stars."""
        stars = '★' * int(obj.rating) + '☆' * (5 - int(obj.rating))
        return format_html(
            '<span style="color: #ffc107; font-size: 16px;">{}</span> ({})',
            stars, obj.rating
        )
    rating_stars.short_description = "Rating"
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'flagged': '#fd7e14',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def would_recommend_icon(self, obj):
        """Display recommendation as icon."""
        if obj.would_recommend:
            return format_html('<span style="color: green; font-size: 16px;">👍</span>')
        return format_html('<span style="color: red; font-size: 16px;">👎</span>')
    would_recommend_icon.short_description = "Recommend"
    
    def helpfulness_score(self, obj):
        """Display helpfulness score."""
        total_votes = obj.helpful_count + obj.not_helpful_count
        if total_votes == 0:
            return "No votes"
        
        helpful_percentage = (obj.helpful_count / total_votes) * 100
        color = "#28a745" if helpful_percentage >= 70 else "#ffc107" if helpful_percentage >= 40 else "#dc3545"
        
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color,
            obj.helpful_count,
            total_votes,
            round(helpful_percentage, 1)
        )
    helpfulness_score.short_description = "Helpful Score"
    
    # Admin actions (same as BraiderReview)
    def approve_reviews(self, request, queryset):
        """Approve selected reviews."""
        updated = queryset.filter(status='pending').update(
            status='approved',
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(request, f'{updated} reviews have been approved.')
    approve_reviews.short_description = "Approve selected reviews"
    
    def reject_reviews(self, request, queryset):
        """Reject selected reviews."""
        updated = queryset.filter(status='pending').update(
            status='rejected',
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(request, f'{updated} reviews have been rejected.')
    reject_reviews.short_description = "Reject selected reviews"
    
    def flag_reviews(self, request, queryset):
        """Flag selected reviews for further review."""
        updated = queryset.update(
            status='flagged',
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(request, f'{updated} reviews have been flagged.')
    flag_reviews.short_description = "Flag selected reviews"


@admin.register(ReviewResponse)
class ReviewResponseAdmin(admin.ModelAdmin):
    """Admin interface for ReviewResponse model."""
    
    list_display = [
        'review_info', 'responder_email', 'response_preview',
        'is_official', 'created_at'
    ]
    list_filter = ['is_official', 'created_at']
    search_fields = ['responder__email', 'response_text']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Response Information', {
            'fields': (
                'id', 'braider_review', 'product_review', 'responder', 'is_official'
            )
        }),
        ('Content', {
            'fields': ('response_text',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'responder', 'braider_review__braider', 'product_review__product'
        )
    
    def review_info(self, obj):
        """Display which review this response belongs to."""
        if obj.braider_review:
            return format_html(
                'Braider Review: {} ({}★)',
                obj.braider_review.braider.name,
                obj.braider_review.overall_rating
            )
        elif obj.product_review:
            return format_html(
                'Product Review: {} ({}★)',
                obj.product_review.product.name,
                obj.product_review.rating
            )
        return "Unknown"
    review_info.short_description = "Review"
    
    def responder_email(self, obj):
        """Display responder email."""
        return obj.responder.email
    responder_email.short_description = "Responder"
    
    def response_preview(self, obj):
        """Display response preview."""
        if len(obj.response_text) > 100:
            return f"{obj.response_text[:100]}..."
        return obj.response_text
    response_preview.short_description = "Response"


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    """Admin interface for ReviewReport model."""
    
    list_display = [
        'review_info', 'reporter_email', 'reason_display',
        'status_badge', 'created_at'
    ]
    list_filter = ['reason', 'status', 'created_at']
    search_fields = ['reporter__email', 'description']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Report Information', {
            'fields': (
                'id', 'braider_review', 'product_review', 'reporter'
            )
        }),
        ('Report Details', {
            'fields': (
                'reason', 'description'
            )
        }),
        ('Moderation', {
            'fields': (
                'status', 'reviewed_by', 'reviewed_at', 'admin_notes'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    actions = ['mark_reviewed', 'mark_resolved', 'mark_dismissed']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'reporter', 'reviewed_by', 'braider_review__braider', 'product_review__product'
        )
    
    def review_info(self, obj):
        """Display which review was reported."""
        if obj.braider_review:
            return format_html(
                'Braider Review: {} ({}★)',
                obj.braider_review.braider.name,
                obj.braider_review.overall_rating
            )
        elif obj.product_review:
            return format_html(
                'Product Review: {} ({}★)',
                obj.product_review.product.name,
                obj.product_review.rating
            )
        return "Unknown"
    review_info.short_description = "Reported Review"
    
    def reporter_email(self, obj):
        """Display reporter email."""
        return obj.reporter.email
    reporter_email.short_description = "Reporter"
    
    def reason_display(self, obj):
        """Display reason with color coding."""
        colors = {
            'inappropriate': '#dc3545',
            'spam': '#fd7e14',
            'fake': '#dc3545',
            'offensive': '#dc3545',
            'irrelevant': '#ffc107',
            'other': '#6c757d',
        }
        color = colors.get(obj.reason, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_reason_display()
        )
    reason_display.short_description = "Reason"
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'reviewed': '#17a2b8',
            'resolved': '#28a745',
            'dismissed': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    # Admin actions
    def mark_reviewed(self, request, queryset):
        """Mark selected reports as reviewed."""
        updated = queryset.filter(status='pending').update(
            status='reviewed',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} reports have been marked as reviewed.')
    mark_reviewed.short_description = "Mark as reviewed"
    
    def mark_resolved(self, request, queryset):
        """Mark selected reports as resolved."""
        updated = queryset.update(
            status='resolved',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} reports have been resolved.')
    mark_resolved.short_description = "Mark as resolved"
    
    def mark_dismissed(self, request, queryset):
        """Dismiss selected reports."""
        updated = queryset.update(
            status='dismissed',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} reports have been dismissed.')
    mark_dismissed.short_description = "Dismiss reports"


@admin.register(ReviewHelpfulness)
class ReviewHelpfulnessAdmin(admin.ModelAdmin):
    """Admin interface for ReviewHelpfulness model."""
    
    list_display = [
        'review_info', 'user_email', 'vote_display', 'created_at'
    ]
    list_filter = ['vote', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'braider_review__braider', 'product_review__product'
        )
    
    def review_info(self, obj):
        """Display which review was voted on."""
        if obj.braider_review:
            return format_html(
                'Braider Review: {} ({}★)',
                obj.braider_review.braider.name,
                obj.braider_review.overall_rating
            )
        elif obj.product_review:
            return format_html(
                'Product Review: {} ({}★)',
                obj.product_review.product.name,
                obj.product_review.rating
            )
        return "Unknown"
    review_info.short_description = "Review"
    
    def user_email(self, obj):
        """Display voter email."""
        return obj.user.email
    user_email.short_description = "Voter"
    
    def vote_display(self, obj):
        """Display vote with color coding."""
        if obj.vote == 'helpful':
            return format_html('<span style="color: green;">👍 Helpful</span>')
        return format_html('<span style="color: red;">👎 Not Helpful</span>')
    vote_display.short_description = "Vote"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False