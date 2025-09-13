# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import (
    LandingPageSettings,
    HeroSection,
    StatItem,
    Company,
    ServiceItem,
    PricingTier,
    Feature,
    Testimonial,
    FAQItem,
    CallToAction,
    SeoSettings
)


@admin.register(LandingPageSettings)
class LandingPageSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_title', 'is_active', 'maintenance_mode', 'updated_at']
    list_filter = ['is_active', 'maintenance_mode']
    search_fields = ['site_title', 'site_description']
    
    fieldsets = (
        ('Informacoes Basicas', {
            'fields': ('site_title', 'site_description', 'meta_keywords')
        }),
        ('Contactos', {
            'fields': ('contact_email', 'contact_phone', 'whatsapp_number')
        }),
        ('Redes Sociais', {
            'fields': ('facebook_url', 'instagram_url', 'linkedin_url', 'youtube_url')
        }),
        ('Analytics', {
            'fields': ('google_analytics_id', 'facebook_pixel_id')
        }),
        ('Configuracoes', {
            'fields': ('is_active', 'maintenance_mode', 'maintenance_message')
        })
    )
    
    def has_add_permission(self, request):
        """Only allow one settings instance"""
        return not LandingPageSettings.objects.exists()


@admin.register(HeroSection)
class HeroSectionAdmin(admin.ModelAdmin):
    list_display = ['headline', 'is_active', 'order', 'updated_at']
    list_filter = ['is_active', 'badge_is_active']
    search_fields = ['headline', 'description']
    list_editable = ['is_active', 'order']
    ordering = ['order']
    
    fieldsets = (
        ('Badge', {
            'fields': ('badge_text', 'badge_is_active')
        }),
        ('Conteudo Principal', {
            'fields': ('headline', 'headline_highlight', 'description')
        }),
        ('Botoes CTA', {
            'fields': ('primary_cta_text', 'primary_cta_url', 'secondary_cta_text', 'secondary_cta_url')
        }),
        ('Prova Social', {
            'fields': ('social_proof_text', 'rating_value', 'rating_count')
        }),
        ('Media', {
            'fields': ('hero_image', 'background_video')
        }),
        ('Configuracoes', {
            'fields': ('is_active', 'order')
        })
    )


@admin.register(StatItem)
class StatItemAdmin(admin.ModelAdmin):
    list_display = ['value', 'label', 'section', 'is_active', 'order']
    list_filter = ['section', 'is_active']
    search_fields = ['value', 'label']
    list_editable = ['is_active', 'order']
    ordering = ['section', 'order']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'show_in_hero', 'show_in_ticker', 'is_active', 'order']
    list_filter = ['category', 'show_in_hero', 'show_in_ticker', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['show_in_hero', 'show_in_ticker', 'is_active', 'order']
    ordering = ['order', 'name']
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;"/>',
                obj.logo.url
            )
        return "Sem logo"
    logo_preview.short_description = "Preview"
    
    readonly_fields = ['logo_preview']


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'student_count', 'level', 'is_featured', 'is_active', 'order']
    list_filter = ['is_featured', 'is_active', 'target_companies']
    search_fields = ['title', 'description']
    list_editable = ['is_featured', 'is_active', 'order']
    ordering = ['order', 'title']
    filter_horizontal = ['target_companies']


@admin.register(PricingTier)
class PricingTierAdmin(admin.ModelAdmin):
    list_display = ['title', 'formatted_monthly_price', 'formatted_yearly_price', 'is_popular', 'is_active', 'order']
    list_filter = ['is_popular', 'is_active', 'currency']
    search_fields = ['title', 'subtitle']
    list_editable = ['is_popular', 'is_active', 'order']
    ordering = ['order']
    
    def formatted_monthly_price(self, obj):
        return f"{obj.monthly_price:,.0f} {obj.currency}"
    formatted_monthly_price.short_description = "Preco Mensal"
    
    def formatted_yearly_price(self, obj):
        return f"{obj.yearly_price:,.0f} {obj.currency}"
    formatted_yearly_price.short_description = "Preco Anual"


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ['title', 'grid_column_span', 'is_highlighted', 'is_active', 'order']
    list_filter = ['is_highlighted', 'is_active', 'grid_column_span']
    search_fields = ['title', 'description']
    list_editable = ['is_highlighted', 'is_active', 'order']
    ordering = ['order']


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'sector', 'rating', 'verified', 'is_featured', 'is_active']
    list_filter = ['sector', 'rating', 'verified', 'is_featured', 'is_active', 'company']
    search_fields = ['name', 'text', 'result_achieved']
    list_editable = ['verified', 'is_featured', 'is_active']
    ordering = ['order', '-date_given']
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px; border-radius: 50%;"/>',
                obj.avatar.url
            )
        return "Sem avatar"
    avatar_preview.short_description = "Avatar"


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ['question_short', 'category', 'is_featured', 'is_active', 'order']
    list_filter = ['category', 'is_featured', 'is_active']
    search_fields = ['question', 'answer', 'keywords']
    list_editable = ['is_featured', 'is_active', 'order']
    ordering = ['category', 'order']
    
    def question_short(self, obj):
        return obj.question[:80] + "..." if len(obj.question) > 80 else obj.question
    question_short.short_description = "Pergunta"


@admin.register(CallToAction)
class CallToActionAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'is_active', 'order']
    list_filter = ['section', 'is_active']
    search_fields = ['title', 'subtitle', 'description']
    list_editable = ['is_active', 'order']
    ordering = ['section', 'order']


@admin.register(SeoSettings)
class SeoSettingsAdmin(admin.ModelAdmin):
    list_display = ['page_type', 'meta_title', 'index_page', 'follow_links']
    list_filter = ['page_type', 'index_page', 'follow_links']
    search_fields = ['meta_title', 'meta_description', 'meta_keywords']


# Custom admin site configuration
admin.site.site_header = "ProEnglish CMS Admin"
admin.site.site_title = "ProEnglish CMS"
admin.site.index_title = "Gestao de Conteudo da Landing Page"