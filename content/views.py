from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Genre, ContentPiece, NewsletterSubscriber
from .serializers import (
    GenreSerializer,
    ContentPieceListSerializer,
    ContentPieceDetailSerializer,
    NewsletterSubscriberSerializer,
)


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
        queryset = super().get_queryset()
        genre = self.request.query_params.get("genre")
        if genre:
            queryset = queryset.filter(genre__slug=genre)
        return queryset.order_by("-published_at")

    @action(detail=False, methods=["get"])
    def search(self, request):
        query = request.query_params.get("search", "")
        if not query:
            return Response([], status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset().filter(
            title__icontains=query
        ) | self.get_queryset().filter(body__icontains=query)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class NewsletterSubscriberViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer
    http_method_names = ['post']

    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        """Subscribe email to newsletter."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(
                    {"message": "Successfully subscribed to newsletter"},
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {"error": "Could not subscribe. Please try again."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# from rest_framework import viewsets
# from .models import Genre, ContentPiece
# from .serializers import GenreSerializer, ContentPieceListSerializer, ContentPieceDetailSerializer


# class GenreViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Genre.objects.all()
#     serializer_class = GenreSerializer
#     lookup_field = "slug"


# class ContentPieceViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = ContentPiece.objects.filter(status="published")
#     lookup_field = "slug"

#     def get_serializer_class(self):
#         if self.action == "retrieve":
#             return ContentPieceDetailSerializer
#         return ContentPieceListSerializer

#     def get_queryset(self):
#         qs = super().get_queryset()
#         genre_slug = self.request.query_params.get("genre")
#         if genre_slug:
#             qs = qs.filter(genre__slug=genre_slug)
#         return qs