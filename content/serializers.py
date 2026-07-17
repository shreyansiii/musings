from rest_framework import serializers
from .models import Genre, Author, Issue, ContentPiece, MediaFile


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "slug", "description", "cover_image"]


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "display_name", "bio", "avatar", "instagram_handle"]


class MediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = ["id", "kind", "file", "caption", "order"]


class ContentPieceListSerializer(serializers.ModelSerializer):
    """Lighter version for the homepage/listing — no full body text."""
    author = AuthorSerializer(read_only=True)
    genre = GenreSerializer(read_only=True)

    class Meta:
        model = ContentPiece
        fields = [
            "id", "title", "slug", "subtitle", "content_type",
            "author", "genre", "cover_image", "is_featured", "published_at",
        ]


class ContentPieceDetailSerializer(serializers.ModelSerializer):
    """Full version for a single article/poem page."""
    author = AuthorSerializer(read_only=True)
    genre = GenreSerializer(read_only=True)
    media_files = MediaFileSerializer(many=True, read_only=True)

    class Meta:
        model = ContentPiece
        fields = [
            "id", "title", "slug", "subtitle", "content_type", "body",
            "author", "genre", "cover_image", "media_files",
            "is_featured", "published_at",
        ]