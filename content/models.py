"""
MUSINGS by Shreyansi — core content models
App: content/models.py

Design principle: ONE flexible ContentPiece model instead of separate
Article/Poem/Video models. A "content_type" field tells us what kind of
piece it is. Media (audio/video/images) attach via a separate MediaFile
table. This keeps things simple now and scales fine to hundreds of pieces.
"""

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.mail import send_mass_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from cloudinary.models import CloudinaryField


# ---------------------------------------------------------------------
# 1. GENRE — Fashion, Street Culture, Music, Spirituality, Sports & Fitness
# ---------------------------------------------------------------------
class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="genres/", blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------
# 2. AUTHOR — wraps Django's built-in User so multiple contributors
#    can be added later without touching auth logic
# ---------------------------------------------------------------------
class Author(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="authors/", blank=True, null=True)
    instagram_handle = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.display_name


# ---------------------------------------------------------------------
# 3. ISSUE — optional grouping, e.g. "Vol. 1: Monsoon" — lets you
#    release content in curated batches instead of a random stream
# ---------------------------------------------------------------------
class Issue(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    theme_note = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="issues/", blank=True, null=True)
    release_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-release_date"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------
# 4. CONTENT PIECE — the heart of the magazine
# ---------------------------------------------------------------------
class ContentPiece(models.Model):
    CONTENT_TYPES = [
        ("article", "Article"),
        ("poem", "Poem"),
        ("audio", "Audio"),
        ("video", "Video"),
        ("photo_essay", "Photo Essay"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_review", "In Review"),
        ("published", "Published"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    subtitle = models.CharField(max_length=250, blank=True)

    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    body = models.TextField(
        blank=True,
        help_text="Main text: article body, poem lines, or video/audio description",
    )

    author = models.ForeignKey(Author, on_delete=models.PROTECT, related_name="pieces")
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="pieces")
    issue = models.ForeignKey(
        Issue, on_delete=models.SET_NULL, null=True, blank=True, related_name="pieces"
    )

    cover_image = models.ImageField(upload_to="covers/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_featured = models.BooleanField(default=False)

    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_content_type_display()})"


# ---------------------------------------------------------------------
# 5. MEDIA FILE — audio/video/extra images attached to a ContentPiece
#    (e.g. an article can have 5 gallery images; a "video" piece has
#    exactly one video file plus maybe a thumbnail)
# ---------------------------------------------------------------------
class MediaFile(models.Model):
    MEDIA_KINDS = [
        ("image", "Image"),
        ("audio", "Audio"),
        ("video", "Video"),
    ]

    content_piece = models.ForeignKey(
        ContentPiece,
        on_delete=models.CASCADE,
        related_name="media_files",
    )

    kind = models.CharField(max_length=10, choices=MEDIA_KINDS)

    file = CloudinaryField(
        resource_type="auto",
        folder="media",
    )

    caption = models.CharField(max_length=200, blank=True)

    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order in gallery",
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.kind} for {self.content_piece.title}"


# ---------------------------------------------------------------------
# 6. NEWSLETTER SUBSCRIBER — email list for newsletter
# ---------------------------------------------------------------------
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email


# ---------------------------------------------------------------------
# 7. COMMENT — reader engagement
# ---------------------------------------------------------------------
class Comment(models.Model):
    content_piece = models.ForeignKey(
        ContentPiece, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user} on {self.content_piece.title}"


# ---------------------------------------------------------------------
# 8. SIGNAL — Send newsletter email when new content is published
# ---------------------------------------------------------------------
@receiver(post_save, sender=ContentPiece)
def send_newsletter_on_publish(sender, instance, created, **kwargs):
    """Send newsletter email to all subscribers when new content is published."""
    # Only send if status is published and published_at is set
    if instance.status == "published" and instance.published_at:
        subscribers = NewsletterSubscriber.objects.filter(is_active=True)
        if not subscribers.exists():
            return

        emails = [sub.email for sub in subscribers]
        subject = f"New: {instance.title} — MUSINGS by Shreyansi"
        
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://musingsby.shreyansi.com')
        
        message = f"""Hi there,

New content from MUSINGS by Shreyansi:

{instance.title}
{instance.subtitle or ''}

Read more: {frontend_url}/piece/{instance.slug}

---
MUSINGS by Shreyansi
An Independent Magazine
        """

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@musingsby.shreyansi.com')
        
        try:
            send_mass_mail(
                [(subject, message, from_email, [email]) for email in emails],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Newsletter send error: {e}")

# Register the signal
post_save.connect(send_newsletter_on_publish, sender=ContentPiece)