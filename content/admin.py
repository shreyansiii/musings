from django.contrib import admin
from .models import Genre, Author, Issue, ContentPiece, MediaFile, Comment


class MediaFileInline(admin.TabularInline):
    model = MediaFile
    extra = 1  # shows 1 empty upload slot by default


@admin.register(ContentPiece)
class ContentPieceAdmin(admin.ModelAdmin):
    inlines = [MediaFileInline]
    list_display = ["title", "content_type", "genre", "status", "published_at"]
    list_filter = ["content_type", "status", "genre"]


admin.site.register(Genre)
admin.site.register(Author)
admin.site.register(Issue)
admin.site.register(Comment)


# from django.contrib import admin
# from .models import Genre, Author, Issue, ContentPiece, MediaFile, Comment

# admin.site.register(Genre)
# admin.site.register(Author)
# admin.site.register(Issue)
# admin.site.register(ContentPiece)
# admin.site.register(MediaFile)
# admin.site.register(Comment)
