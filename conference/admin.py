from django.contrib import admin, messages

from assistant.retrieval import embed_documents
from conference.indexing import content_hash, sync_session_chunks
from conference.models import KnowledgeChunk, Session, Speaker

admin.site.site_header = "Django Pub AI — база знань"
admin.site.site_title = "База знань"
admin.site.index_title = "Контекст для RAG"


class KnowledgeChunkInline(admin.StackedInline):
    model = KnowledgeChunk
    extra = 0
    fields = ("content", "content_hash")
    readonly_fields = ("content_hash",)
    show_change_link = True


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "is_placeholder")
    list_filter = ("is_placeholder",)
    search_fields = ("name", "bio", "role")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("position", "block_number", "kind", "title", "duration_min")
    list_filter = ("kind", "block_number")
    search_fields = ("title", "body", "stack")
    filter_horizontal = ("speakers",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = (KnowledgeChunkInline,)
    actions = ("rebuild_chunks",)

    def save_formset(self, request, form, formset, change):
        pending = []
        for inline_form in formset.forms:
            cleaned = getattr(inline_form, "cleaned_data", None)
            if not cleaned or cleaned.get("DELETE"):
                continue
            obj = inline_form.instance
            if not isinstance(obj, KnowledgeChunk):
                continue
            if obj.pk and "content" not in inline_form.changed_data:
                continue
            obj.content_hash = content_hash(obj.content)
            pending.append(obj)
        if pending:
            vectors = embed_documents([chunk.content for chunk in pending])
            for chunk, vector in zip(pending, vectors, strict=True):
                chunk.embedding = vector
        super().save_formset(request, form, formset, change)

    @admin.action(description="Перебудувати фрагменти бази знань з тексту сесії")
    def rebuild_chunks(self, request, queryset):
        created = 0
        removed = 0
        for session in queryset.prefetch_related("speakers"):
            new_count, removed_count = sync_session_chunks(session)
            created += new_count
            removed += removed_count
        self.message_user(
            request,
            f"Оновлено контекст: нових фрагментів {created}, видалено застарілих {removed}.",
            messages.SUCCESS,
        )


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("session", "excerpt", "content_hash")
    list_filter = ("session",)
    search_fields = ("content", "session__title")
    readonly_fields = ("content_hash",)
    fields = ("session", "content", "content_hash")

    @admin.display(description="Фрагмент")
    def excerpt(self, obj: KnowledgeChunk) -> str:
        text = " ".join(obj.content.split())
        return text[:120]

    def save_model(self, request, obj, form, change):
        obj.content_hash = content_hash(obj.content)
        if not change or "content" in form.changed_data:
            obj.embedding = embed_documents([obj.content])[0]
        super().save_model(request, obj, form, change)
