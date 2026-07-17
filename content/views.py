from rest_framework import viewsets
from .models import Genre, ContentPiece
from .serializers import GenreSerializer, ContentPieceListSerializer, ContentPieceDetailSerializer


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    lookup_field = "slug"


class ContentPieceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ContentPiece.objects.filter(status="published")
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ContentPieceDetailSerializer
        return ContentPieceListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        genre_slug = self.request.query_params.get("genre")
        if genre_slug:
            qs = qs.filter(genre__slug=genre_slug)
        return qs