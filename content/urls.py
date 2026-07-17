from rest_framework.routers import DefaultRouter
from .views import GenreViewSet, ContentPieceViewSet

router = DefaultRouter()
router.register("genres", GenreViewSet, basename="genre")
router.register("content-pieces", ContentPieceViewSet, basename="content-piece")

urlpatterns = router.urls