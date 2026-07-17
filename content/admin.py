from django.contrib import admin
from .models import Genre, Author, Issue, ContentPiece, MediaFile, Comment

admin.site.register(Genre)
admin.site.register(Author)
admin.site.register(Issue)
admin.site.register(ContentPiece)
admin.site.register(MediaFile)
admin.site.register(Comment)
