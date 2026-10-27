from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from conference.models import KnowledgeChunk


class Command(BaseCommand):
    help = "Зберігає базу знань (спікери, сесії, фрагменти з ембедингами) у дамп для репозиторію."

    def handle(self, *args, **options):
        dump = settings.KNOWLEDGE_DUMP
        dump.parent.mkdir(parents=True, exist_ok=True)
        call_command(
            "dumpdata",
            "conference.speaker",
            "conference.session",
            "conference.knowledgechunk",
            output=str(dump),
            verbosity=0,
        )
        size_kb = dump.stat().st_size // 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"Дамп {dump.name}: фрагментів {KnowledgeChunk.objects.count()}, {size_kb} КБ."
            )
        )
