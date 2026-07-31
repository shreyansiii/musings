from django import forms
from django.contrib import admin
from tinymce.widgets import TinyMCE

from .models import (
    Genre,
    Author,
    Issue,
    ContentPiece,
    MediaFile,
    Comment,
    NewsletterSubscriber,
)


class ContentPieceAdminForm(forms.ModelForm):
    body = forms.CharField(
        widget=TinyMCE(
            attrs={
                "cols": 80,
                "rows": 30,
            }
        ),
        required=False,
    )

    class Meta:
        model = ContentPiece
        fields = "__all__"


class MediaFileInline(admin.TabularInline):
    model = MediaFile
    extra = 1


@admin.register(ContentPiece)
class ContentPieceAdmin(admin.ModelAdmin):
    form = ContentPieceAdminForm

    inlines = [MediaFileInline]

    list_display = [
        "title",
        "content_type",
        "genre",
        "status",
        "published_at",
    ]

    list_filter = [
        "content_type",
        "status",
        "genre",
    ]


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "subscribed_at",
        "is_active",
    ]

    list_filter = [
        "is_active",
        "subscribed_at",
    ]

    search_fields = [
        "email",
    ]

    readonly_fields = [
        "subscribed_at",
    ]


admin.site.register(Genre)
admin.site.register(Author)
admin.site.register(Issue)
admin.site.register(Comment)




# from django.contrib import admin
# from .models import Genre, Author, Issue, ContentPiece, MediaFile, Comment, NewsletterSubscriber


# class MediaFileInline(admin.TabularInline):
#     model = MediaFile
#     extra = 1  # shows 1 empty upload slot by default


# @admin.register(ContentPiece)
# class ContentPieceAdmin(admin.ModelAdmin):
#     inlines = [MediaFileInline]
#     list_display = ["title", "content_type", "genre", "status", "published_at"]
#     list_filter = ["content_type", "status", "genre"]


# @admin.register(NewsletterSubscriber)
# class NewsletterSubscriberAdmin(admin.ModelAdmin):
#     list_display = ['email', 'subscribed_at', 'is_active']
#     list_filter = ['is_active', 'subscribed_at']
#     search_fields = ['email']
#     readonly_fields = ['subscribed_at']


# admin.site.register(Genre)
# admin.site.register(Author)
# admin.site.register(Issue)
# admin.site.register(Comment)
