from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.mail import EmailMessage
from django.conf import settings
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


class ContactMessageView(APIView):
    """Receives contact form submissions and emails them to the site owner."""

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip()
        message = (request.data.get("message") or "").strip()

        if not name or not email or not message:
            return Response(
                {"error": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "onboarding@resend.dev")
            notification = EmailMessage(
                subject=f"New contact form message from {name}",
                body=f"From: {name} <{email}>\n\n{message}",
                from_email=from_email,
                to=["shreyansishrestha@gmail.com"],
                reply_to=[email],
            )
            notification.send(fail_silently=False)
            return Response({"message": "Message sent successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"[CONTACT] Send error: {type(e).__name__}: {e}")
            return Response(
                {"error": "Could not send message. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

# from rest_framework import viewsets, status
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from .models import Genre, ContentPiece, NewsletterSubscriber
# from .serializers import (
#     GenreSerializer,
#     ContentPieceListSerializer,
#     ContentPieceDetailSerializer,
#     NewsletterSubscriberSerializer,
# )


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
#         queryset = super().get_queryset()
#         genre = self.request.query_params.get("genre")
#         if genre:
#             queryset = queryset.filter(genre__slug=genre)
#         return queryset.order_by("-published_at")

#     @action(detail=False, methods=["get"])
#     def search(self, request):
#         query = request.query_params.get("search", "")
#         if not query:
#             return Response([], status=status.HTTP_400_BAD_REQUEST)
#         queryset = self.get_queryset().filter(
#             title__icontains=query
#         ) | self.get_queryset().filter(body__icontains=query)
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)


# class NewsletterSubscriberViewSet(viewsets.ModelViewSet):
#     queryset = NewsletterSubscriber.objects.all()
#     serializer_class = NewsletterSubscriberSerializer
#     http_method_names = ['post']

#     @action(detail=False, methods=['post'])
#     def subscribe(self, request):
#         """Subscribe email to newsletter."""
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             try:
#                 serializer.save()
#                 return Response(
#                     {"message": "Successfully subscribed to newsletter"},
#                     status=status.HTTP_201_CREATED
#                 )
#             except Exception as e:
#                 return Response(
#                     {"error": "Could not subscribe. Please try again."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



    
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