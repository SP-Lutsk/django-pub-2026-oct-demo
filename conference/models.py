from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from conference.indexes import HnswIndex


class Speaker(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    is_placeholder = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Спікер"
        verbose_name_plural = "Спікери"

    def __str__(self) -> str:
        return self.name


class Session(models.Model):
    class Kind(models.TextChoices):
        TALK = "talk", "Доповідь"
        DISCUSSION = "discussion", "Дискусія"
        STUDENT = "student", "Виступи студентів"
        REFERENCE = "reference", "Технічний довідник"

    slug = models.SlugField(unique=True)
    block_number = models.PositiveSmallIntegerField()
    position = models.PositiveSmallIntegerField(default=0)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=300)
    stack = models.CharField(max_length=500, blank=True)
    duration_min = models.PositiveSmallIntegerField(default=15)
    speakers = models.ManyToManyField(Speaker, blank=True, related_name="sessions")
    body = models.TextField()

    class Meta:
        ordering = ["position", "block_number"]
        verbose_name = "Сесія"
        verbose_name_plural = "Сесії"

    def __str__(self) -> str:
        return self.title


class KnowledgeChunk(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="chunks")
    content = models.TextField()
    content_hash = models.CharField(max_length=64, unique=True)
    embedding = VectorField(dimensions=settings.EMBEDDING_DIMENSIONS)

    class Meta:
        indexes = [
            HnswIndex(
                name="kc_embedding_hnsw",
                fields=["embedding"],
                opclasses=["vector_cosine_ops"],
                m=16,
                ef_construction=64,
            )
        ]
        verbose_name = "Фрагмент бази знань"
        verbose_name_plural = "Фрагменти бази знань"

    def __str__(self) -> str:
        return f"{self.session.slug}:{self.content_hash[:8]}"


class ChatLog(models.Model):
    question = models.TextField()
    answer = models.TextField(blank=True)
    top_similarity = models.FloatField(null=True, blank=True)
    grounded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.question[:80]
