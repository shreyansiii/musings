"""
MUSINGS by Shreyansi — core content models
App: content/models.py

Design principle: ONE flexible ContentPiece model instead of separate
Article/Poem/Video models. A "content_type" field tells us what kind of
piece it is. Media (audio/video/images) attach via a separate MediaFile
table. This keeps things simple now and scales fine to hundreds of pieces.
"""

import threading

from django.db import models, transaction
from django.conf import settings
from django.utils.text import slugify
from django.core.mail import EmailMultiAlternatives
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

    # Tracks whether the publish-newsletter has already gone out for this
    # piece, so re-saving/editing an already-published piece never
    # re-triggers a full subscriber blast.
    newsletter_sent = models.BooleanField(default=False)

    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while ContentPiece.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
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
#
# Sends a styled HTML email (with plain-text fallback) to each active
# subscriber individually, via EmailMultiAlternatives. Fires only once
# per piece thanks to the newsletter_sent flag, and runs on a
# background thread after the DB commit so publishing in the admin
# stays fast.
# ---------------------------------------------------------------------

NEWSLETTER_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
  <body style="margin:0; padding:0; background-color:#f4f1ec; font-family: Georgia, 'Times New Roman', serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f1ec; padding:32px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06);">

            <!-- Header -->
            <tr>
              <td style="background-color:#1a1a1a; padding:24px 32px; text-align:center;">
                <span style="color:#f4f1ec; font-size:13px; letter-spacing:3px; text-transform:uppercase;">MUSINGS by Shreyansi</span>
              </td>
            </tr>

            {cover_image_block}

            <!-- Body -->
            <tr>
              <td style="padding:36px 40px;">
                <p style="margin:0 0 8px 0; font-size:12px; letter-spacing:2px; text-transform:uppercase; color:#a08a6a;">New {content_type_label}</p>
                <h1 style="margin:0 0 12px 0; font-size:28px; line-height:1.3; color:#1a1a1a;">{title}</h1>
                {subtitle_block}
                <p style="margin:24px 0 0 0; font-size:15px; line-height:1.7; color:#444444;">{excerpt}</p>

                <table role="presentation" cellpadding="0" cellspacing="0" style="margin:32px 0 0 0;">
                  <tr>
                    <td style="background-color:#1a1a1a; border-radius:4px;">
                      <a href="{read_url}" style="display:inline-block; padding:14px 28px; color:#f4f1ec; text-decoration:none; font-size:14px; letter-spacing:1px; text-transform:uppercase;">Read the Piece</a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding:24px 40px; background-color:#f4f1ec; text-align:center;">
                <p style="margin:0; font-size:12px; color:#999999;">MUSINGS by Shreyansi — An Independent Magazine</p>
                <p style="margin:8px 0 0 0; font-size:11px; color:#bbbbbb;">You're receiving this because you subscribed at musingsby.shreyansi.com</p>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _do_send_newsletter(content_piece_id, title, subtitle, slug, content_type_label, body, cover_image_url):
    print(f"[NEWSLETTER] Background thread started for piece {content_piece_id}")
    try:
        subscribers = NewsletterSubscriber.objects.filter(is_active=True)
        emails = list(subscribers.values_list("email", flat=True))
        print(f"[NEWSLETTER] Found {len(emails)} active subscriber(s): {emails}")
        if not emails:
            print("[NEWSLETTER] No active subscribers, aborting send.")
            return

        frontend_url = getattr(settings, "FRONTEND_URL", "https://musingsby.shreyansi.com")
        read_url = f"{frontend_url}/piece/{slug}"
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER

        excerpt = (body or "").strip()
        if len(excerpt) > 280:
            excerpt = excerpt[:280].rsplit(" ", 1)[0] + "…"

        subtitle_block = (
            f'<p style="margin:0; font-size:16px; color:#777777; font-style:italic;">{subtitle}</p>'
            if subtitle else ""
        )
        cover_image_block = (
            f'''<tr><td style="padding:0;"><img src="{cover_image_url}" alt="" width="600" style="display:block; width:100%; height:auto;"/></td></tr>'''
            if cover_image_url else ""
        )

        html_body = NEWSLETTER_HTML_TEMPLATE.format(
            title=title,
            subtitle_block=subtitle_block,
            content_type_label=content_type_label,
            excerpt=excerpt,
            read_url=read_url,
            cover_image_block=cover_image_block,
        )

        plain_body = f"""New {content_type_label} — MUSINGS by Shreyansi

{title}
{subtitle or ''}

{excerpt}

Read more: {read_url}

---
MUSINGS by Shreyansi
An Independent Magazine
"""

        subject = f"New: {title} — MUSINGS by Shreyansi"
        sent_count = 0

        for email in emails:
            msg = EmailMultiAlternatives(subject, plain_body, from_email, [email])
            msg.attach_alternative(html_body, "text/html")
            msg.send()
            sent_count += 1

        print(f"[NEWSLETTER] Sent {sent_count}/{len(emails)} email(s) successfully")

        ContentPiece.objects.filter(pk=content_piece_id).update(newsletter_sent=True)
        print(f"[NEWSLETTER] Marked piece {content_piece_id} as newsletter_sent=True")
    except Exception as e:
        print(f"[NEWSLETTER] SEND ERROR: {type(e).__name__}: {e}")


@receiver(post_save, sender=ContentPiece)
def send_newsletter_on_publish(sender, instance, created, **kwargs):
    print(
        f"[NEWSLETTER] Signal fired for '{instance.title}' — "
        f"status={instance.status}, published_at={instance.published_at}, "
        f"newsletter_sent={instance.newsletter_sent}"
    )
    if (
        instance.status == "published"
        and instance.published_at
        and not instance.newsletter_sent
    ):
        print(f"[NEWSLETTER] Conditions met, scheduling send for piece {instance.pk}")
        cover_image_url = instance.cover_image.url if instance.cover_image else None
        args = (
            instance.pk,
            instance.title,
            instance.subtitle,
            instance.slug,
            instance.get_content_type_display(),
            instance.body,
            cover_image_url,
        )
        transaction.on_commit(lambda: threading.Thread(target=_do_send_newsletter, args=args, daemon=True).start())
    else:
        print(f"[NEWSLETTER] Conditions NOT met, skipping send for piece {instance.pk}")





# """
# MUSINGS by Shreyansi — core content models
# App: content/models.py

# Design principle: ONE flexible ContentPiece model instead of separate
# Article/Poem/Video models. A "content_type" field tells us what kind of
# piece it is. Media (audio/video/images) attach via a separate MediaFile
# table. This keeps things simple now and scales fine to hundreds of pieces.
# """

# import threading

# from django.db import models, transaction
# from django.conf import settings
# from django.utils.text import slugify
# from django.core.mail import EmailMultiAlternatives
# from django.db.models.signals import post_save
# from django.dispatch import receiver

# from cloudinary.models import CloudinaryField


# # ---------------------------------------------------------------------
# # 1. GENRE — Fashion, Street Culture, Music, Spirituality, Sports & Fitness
# # ---------------------------------------------------------------------
# class Genre(models.Model):
#     name = models.CharField(max_length=50, unique=True)
#     slug = models.SlugField(max_length=60, unique=True, blank=True)
#     description = models.TextField(blank=True)
#     cover_image = models.ImageField(upload_to="genres/", blank=True, null=True)

#     class Meta:
#         ordering = ["name"]

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.name


# # ---------------------------------------------------------------------
# # 2. AUTHOR — wraps Django's built-in User so multiple contributors
# #    can be added later without touching auth logic
# # ---------------------------------------------------------------------
# class Author(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     display_name = models.CharField(max_length=100)
#     bio = models.TextField(blank=True)
#     avatar = models.ImageField(upload_to="authors/", blank=True, null=True)
#     instagram_handle = models.CharField(max_length=50, blank=True)

#     def __str__(self):
#         return self.display_name


# # ---------------------------------------------------------------------
# # 3. ISSUE — optional grouping, e.g. "Vol. 1: Monsoon" — lets you
# #    release content in curated batches instead of a random stream
# # ---------------------------------------------------------------------
# class Issue(models.Model):
#     title = models.CharField(max_length=100)
#     slug = models.SlugField(max_length=110, unique=True, blank=True)
#     theme_note = models.TextField(blank=True)
#     cover_image = models.ImageField(upload_to="issues/", blank=True, null=True)
#     release_date = models.DateField(null=True, blank=True)

#     class Meta:
#         ordering = ["-release_date"]

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.title)
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.title


# # ---------------------------------------------------------------------
# # 4. CONTENT PIECE — the heart of the magazine
# # ---------------------------------------------------------------------
# class ContentPiece(models.Model):
#     CONTENT_TYPES = [
#         ("article", "Article"),
#         ("poem", "Poem"),
#         ("audio", "Audio"),
#         ("video", "Video"),
#         ("photo_essay", "Photo Essay"),
#     ]
#     STATUS_CHOICES = [
#         ("draft", "Draft"),
#         ("in_review", "In Review"),
#         ("published", "Published"),
#     ]

#     title = models.CharField(max_length=200)
#     slug = models.SlugField(max_length=220, unique=True, blank=True)
#     subtitle = models.CharField(max_length=250, blank=True)

#     content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
#     body = models.TextField(
#         blank=True,
#         help_text="Main text: article body, poem lines, or video/audio description",
#     )

#     author = models.ForeignKey(Author, on_delete=models.PROTECT, related_name="pieces")
#     genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="pieces")
#     issue = models.ForeignKey(
#         Issue, on_delete=models.SET_NULL, null=True, blank=True, related_name="pieces"
#     )

#     cover_image = models.ImageField(upload_to="covers/", blank=True, null=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
#     is_featured = models.BooleanField(default=False)

#     # Tracks whether the publish-newsletter has already gone out for this
#     # piece, so re-saving/editing an already-published piece never
#     # re-triggers a full subscriber blast.
#     newsletter_sent = models.BooleanField(default=False)

#     published_at = models.DateTimeField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ["-published_at", "-created_at"]

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             base_slug = slugify(self.title)
#             slug = base_slug
#             counter = 1
#             while ContentPiece.objects.filter(slug=slug).exclude(pk=self.pk).exists():
#                 slug = f"{base_slug}-{counter}"
#                 counter += 1
#             self.slug = slug
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.title} ({self.get_content_type_display()})"


# # ---------------------------------------------------------------------
# # 5. MEDIA FILE — audio/video/extra images attached to a ContentPiece
# #    (e.g. an article can have 5 gallery images; a "video" piece has
# #    exactly one video file plus maybe a thumbnail)
# # ---------------------------------------------------------------------
# class MediaFile(models.Model):
#     MEDIA_KINDS = [
#         ("image", "Image"),
#         ("audio", "Audio"),
#         ("video", "Video"),
#     ]

#     content_piece = models.ForeignKey(
#         ContentPiece,
#         on_delete=models.CASCADE,
#         related_name="media_files",
#     )

#     kind = models.CharField(max_length=10, choices=MEDIA_KINDS)

#     file = CloudinaryField(
#         resource_type="auto",
#         folder="media",
#     )

#     caption = models.CharField(max_length=200, blank=True)

#     order = models.PositiveIntegerField(
#         default=0,
#         help_text="Display order in gallery",
#     )

#     class Meta:
#         ordering = ["order", "id"]

#     def __str__(self):
#         return f"{self.kind} for {self.content_piece.title}"


# # ---------------------------------------------------------------------
# # 6. NEWSLETTER SUBSCRIBER — email list for newsletter
# # ---------------------------------------------------------------------
# class NewsletterSubscriber(models.Model):
#     email = models.EmailField(unique=True)
#     subscribed_at = models.DateTimeField(auto_now_add=True)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         ordering = ["-subscribed_at"]

#     def __str__(self):
#         return self.email


# # ---------------------------------------------------------------------
# # 7. COMMENT — reader engagement
# # ---------------------------------------------------------------------
# class Comment(models.Model):
#     content_piece = models.ForeignKey(
#         ContentPiece, on_delete=models.CASCADE, related_name="comments"
#     )
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     body = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ["created_at"]

#     def __str__(self):
#         return f"Comment by {self.user} on {self.content_piece.title}"


# # ---------------------------------------------------------------------
# # 8. SIGNAL — Send newsletter email when new content is published
# #
# # Sends a styled HTML email (with plain-text fallback) to each active
# # subscriber individually, via EmailMultiAlternatives. Fires only once
# # per piece thanks to the newsletter_sent flag, and runs on a
# # background thread after the DB commit so publishing in the admin
# # stays fast.
# # ---------------------------------------------------------------------

# NEWSLETTER_HTML_TEMPLATE = """\
# <!DOCTYPE html>
# <html>
#   <body style="margin:0; padding:0; background-color:#f4f1ec; font-family: Georgia, 'Times New Roman', serif;">
#     <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f1ec; padding:32px 0;">
#       <tr>
#         <td align="center">
#           <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06);">

#             <!-- Header -->
#             <tr>
#               <td style="background-color:#1a1a1a; padding:24px 32px; text-align:center;">
#                 <span style="color:#f4f1ec; font-size:13px; letter-spacing:3px; text-transform:uppercase;">MUSINGS by Shreyansi</span>
#               </td>
#             </tr>

#             {cover_image_block}

#             <!-- Body -->
#             <tr>
#               <td style="padding:36px 40px;">
#                 <p style="margin:0 0 8px 0; font-size:12px; letter-spacing:2px; text-transform:uppercase; color:#a08a6a;">New {content_type_label}</p>
#                 <h1 style="margin:0 0 12px 0; font-size:28px; line-height:1.3; color:#1a1a1a;">{title}</h1>
#                 {subtitle_block}
#                 <p style="margin:24px 0 0 0; font-size:15px; line-height:1.7; color:#444444;">{excerpt}</p>

#                 <table role="presentation" cellpadding="0" cellspacing="0" style="margin:32px 0 0 0;">
#                   <tr>
#                     <td style="background-color:#1a1a1a; border-radius:4px;">
#                       <a href="{read_url}" style="display:inline-block; padding:14px 28px; color:#f4f1ec; text-decoration:none; font-size:14px; letter-spacing:1px; text-transform:uppercase;">Read the Piece</a>
#                     </td>
#                   </tr>
#                 </table>
#               </td>
#             </tr>

#             <!-- Footer -->
#             <tr>
#               <td style="padding:24px 40px; background-color:#f4f1ec; text-align:center;">
#                 <p style="margin:0; font-size:12px; color:#999999;">MUSINGS by Shreyansi — An Independent Magazine</p>
#                 <p style="margin:8px 0 0 0; font-size:11px; color:#bbbbbb;">You're receiving this because you subscribed at musingsby.shreyansi.com</p>
#               </td>
#             </tr>

#           </table>
#         </td>
#       </tr>
#     </table>
#   </body>
# </html>
# """


# def _do_send_newsletter(content_piece_id, title, subtitle, slug, content_type_label, body, cover_image_url):
#     print(f"[NEWSLETTER] Background thread started for piece {content_piece_id}")
#     try:
#         subscribers = NewsletterSubscriber.objects.filter(is_active=True)
#         emails = list(subscribers.values_list("email", flat=True))
#         print(f"[NEWSLETTER] Found {len(emails)} active subscriber(s): {emails}")
#         if not emails:
#             print("[NEWSLETTER] No active subscribers, aborting send.")
#             return

#         frontend_url = getattr(settings, "FRONTEND_URL", "https://musingsby.shreyansi.com")
#         read_url = f"{frontend_url}/piece/{slug}"
#         from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@musingsby.shreyansi.com")

#         excerpt = (body or "").strip()
#         if len(excerpt) > 280:
#             excerpt = excerpt[:280].rsplit(" ", 1)[0] + "…"

#         subtitle_block = (
#             f'<p style="margin:0; font-size:16px; color:#777777; font-style:italic;">{subtitle}</p>'
#             if subtitle else ""
#         )
#         cover_image_block = (
#             f'''<tr><td style="padding:0;"><img src="{cover_image_url}" alt="" width="600" style="display:block; width:100%; height:auto;"/></td></tr>'''
#             if cover_image_url else ""
#         )

#         html_body = NEWSLETTER_HTML_TEMPLATE.format(
#             title=title,
#             subtitle_block=subtitle_block,
#             content_type_label=content_type_label,
#             excerpt=excerpt,
#             read_url=read_url,
#             cover_image_block=cover_image_block,
#         )

#         plain_body = f"""New {content_type_label} — MUSINGS by Shreyansi

# {title}
# {subtitle or ''}

# {excerpt}

# Read more: {read_url}

# ---
# MUSINGS by Shreyansi
# An Independent Magazine
# """

#         subject = f"New: {title} — MUSINGS by Shreyansi"
#         sent_count = 0

#         for email in emails:
#             msg = EmailMultiAlternatives(subject, plain_body, from_email, [email])
#             msg.attach_alternative(html_body, "text/html")
#             msg.send()
#             sent_count += 1

#         print(f"[NEWSLETTER] Sent {sent_count}/{len(emails)} email(s) successfully")

#         ContentPiece.objects.filter(pk=content_piece_id).update(newsletter_sent=True)
#         print(f"[NEWSLETTER] Marked piece {content_piece_id} as newsletter_sent=True")
#     except Exception as e:
#         print(f"[NEWSLETTER] SEND ERROR: {type(e).__name__}: {e}")


# @receiver(post_save, sender=ContentPiece)
# def send_newsletter_on_publish(sender, instance, created, **kwargs):
#     print(
#         f"[NEWSLETTER] Signal fired for '{instance.title}' — "
#         f"status={instance.status}, published_at={instance.published_at}, "
#         f"newsletter_sent={instance.newsletter_sent}"
#     )
#     if (
#         instance.status == "published"
#         and instance.published_at
#         and not instance.newsletter_sent
#     ):
#         print(f"[NEWSLETTER] Conditions met, scheduling send for piece {instance.pk}")
#         cover_image_url = instance.cover_image.url if instance.cover_image else None
#         args = (
#             instance.pk,
#             instance.title,
#             instance.subtitle,
#             instance.slug,
#             instance.get_content_type_display(),
#             instance.body,
#             cover_image_url,
#         )
#         transaction.on_commit(lambda: threading.Thread(target=_do_send_newsletter, args=args, daemon=True).start())
#     else:
#         print(f"[NEWSLETTER] Conditions NOT met, skipping send for piece {instance.pk}")





