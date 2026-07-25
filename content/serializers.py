from rest_framework import serializers
from .models import Genre, Author, Issue, ContentPiece, MediaFile, NewsletterSubscriber


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "slug", "description", "cover_image"]


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "display_name", "bio", "avatar", "instagram_handle"]


class MediaFileSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = MediaFile
        fields = ["id", "kind", "file", "caption", "order"]

    def get_file(self, obj):
        return obj.file.url if obj.file else None


class ContentPieceListSerializer(serializers.ModelSerializer):
    """Lighter version for the homepage/listing — no full body text."""
    author = AuthorSerializer(read_only=True)
    genre = GenreSerializer(read_only=True)
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = ContentPiece
        fields = [
            "id", "title", "slug", "subtitle", "content_type",
            "author", "genre", "cover_image", "is_featured", "published_at",
            "excerpt",
        ]

    def get_excerpt(self, obj):
        body = getattr(obj, "body", "") or ""
        clean = body.strip()
        max_len = 160
        if len(clean) <= max_len:
            return clean
        return clean[:max_len].rstrip() + "…"


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


class NewsletterSubscriberSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def create(self, validated_data):
        email = validated_data['email']
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={'is_active': True}
        )
        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save()
        return subscriber