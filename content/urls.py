from rest_framework.routers import DefaultRouter
from .views import GenreViewSet, ContentPieceViewSet, NewsletterSubscriberViewSet

router = DefaultRouter()
router.register("genres", GenreViewSet, basename="genre")
router.register("content-pieces", ContentPieceViewSet, basename="content-piece")
router.register("newsletter", NewsletterSubscriberViewSet, basename="newsletter")

urlpatterns = router.urls