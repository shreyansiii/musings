
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    GenreViewSet,
    ContentPieceViewSet,
    NewsletterSubscriberViewSet,
    ContactMessageView,
    health_check,
)

router = DefaultRouter()
router.register("genres", GenreViewSet, basename="genre")
router.register("content-pieces", ContentPieceViewSet, basename="content-piece")
router.register("newsletter", NewsletterSubscriberViewSet, basename="newsletter")

urlpatterns = router.urls + [
    path("contact/", ContactMessageView.as_view(), name="contact-message"),
    path("health/", health_check, name="health-check"),
]





# from django.urls import path
# from rest_framework.routers import DefaultRouter
# from .views import (
#     GenreViewSet,
#     ContentPieceViewSet,
#     NewsletterSubscriberViewSet,
#     ContactMessageView,
# )

# router = DefaultRouter()
# router.register("genres", GenreViewSet, basename="genre")
# router.register("content-pieces", ContentPieceViewSet, basename="content-piece")
# router.register("newsletter", NewsletterSubscriberViewSet, basename="newsletter")

# urlpatterns = router.urls + [
#     path("contact/", ContactMessageView.as_view(), name="contact-message"),
# ]

