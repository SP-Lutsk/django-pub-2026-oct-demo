import logging
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from assistant.retrieval import embed_documents
from conference.indexing import chunk_rows_for_session
from conference.models import KnowledgeChunk, Session, Speaker

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Індексує матеріали Django Pub AI Edition у pgvector."

    def handle(self, *args, **options):
        if not settings.OPENAI_API_KEY:
            raise CommandError("Задайте OPENAI_API_KEY у файлі .env перед індексацією.")

        source_dir = Path(settings.KNOWLEDGE_SOURCE_DIR)
        agenda_path = source_dir / "event_materials.yaml"
        tech_path = source_dir / "tech_knowledge.yaml"
        if not agenda_path.exists():
            raise CommandError(
                f"Немає {agenda_path}. Вихідні матеріали не входять у репозиторій; "
                "учасникам достатньо готового дампу (python manage.py load_knowledge)."
            )
        agenda = yaml.safe_load(agenda_path.read_text(encoding="utf-8"))
        tech = yaml.safe_load(tech_path.read_text(encoding="utf-8")) or {}
        speakers = self._upsert_speakers(agenda.get("speakers", []))
        rows = list(agenda.get("sessions", []))
        for offset, topic in enumerate(tech.get("topics", []), start=100):
            rows.append(
                {
                    **topic,
                    "kind": Session.Kind.REFERENCE,
                    "position": topic.get("position", offset),
                    "duration_min": topic.get("duration_min", 0),
                }
            )
        sessions = self._upsert_sessions(rows, speakers)
        Session.objects.exclude(slug__in=[session.slug for session in sessions]).delete()
        Speaker.objects.exclude(slug__in=speakers).delete()
        pending = self._pending_chunks(sessions)
        if pending:
            logger.info(
                "seeding %s new chunks from %s with %s",
                len(pending),
                agenda_path,
                settings.OPENAI_EMBEDDING_MODEL,
            )
            vectors = embed_documents([item["content"] for item in pending])
            KnowledgeChunk.objects.bulk_create(
                [
                    KnowledgeChunk(
                        session=item["session"],
                        content=item["content"],
                        content_hash=item["content_hash"],
                        embedding=vector,
                    )
                    for item, vector in zip(pending, vectors, strict=True)
                ]
            )
        keep = {item["content_hash"] for item in self._all_chunk_rows(sessions)}
        removed, _ = KnowledgeChunk.objects.exclude(content_hash__in=keep).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Сесій: {len(sessions)}. Нових фрагментів: {len(pending)}. Видалено застарілих: {removed}."
            )
        )

    def _upsert_speakers(self, rows: list[dict]) -> dict[str, Speaker]:
        speakers = {}
        for row in rows:
            speaker, _ = Speaker.objects.update_or_create(
                slug=row["slug"],
                defaults={
                    "name": row["name"],
                    "role": row.get("role", ""),
                    "bio": row.get("bio", ""),
                    "is_placeholder": bool(row.get("is_placeholder", False)),
                },
            )
            speakers[speaker.slug] = speaker
        return speakers

    def _upsert_sessions(self, rows: list[dict], speakers: dict[str, Speaker]) -> list[Session]:
        sessions = []
        for row in rows:
            paragraphs = [part.strip() for part in row.get("paragraphs", []) if str(part).strip()]
            body = "\n\n".join(paragraphs)
            session, _ = Session.objects.update_or_create(
                slug=row["slug"],
                defaults={
                    "block_number": row["block_number"],
                    "position": row.get("position", 0),
                    "kind": row["kind"],
                    "title": row["title"],
                    "stack": row.get("stack", ""),
                    "duration_min": row.get("duration_min", 15),
                    "body": body,
                },
            )
            selected = []
            for slug in row.get("speakers", []):
                if slug not in speakers:
                    raise CommandError(f"Невідомий спікер '{slug}' у сесії '{row['slug']}'.")
                selected.append(speakers[slug])
            session.speakers.set(selected)
            sessions.append(session)
        return sessions

    def _pending_chunks(self, sessions: list[Session]) -> list[dict]:
        rows = self._all_chunk_rows(sessions)
        existing = set(
            KnowledgeChunk.objects.filter(
                content_hash__in=[row["content_hash"] for row in rows]
            ).values_list("content_hash", flat=True)
        )
        return [row for row in rows if row["content_hash"] not in existing]

    def _all_chunk_rows(self, sessions: list[Session]) -> list[dict]:
        rows = []
        for session in sessions:
            rows.extend(chunk_rows_for_session(session))
        return rows
