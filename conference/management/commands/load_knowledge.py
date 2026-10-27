from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from conference.models import KnowledgeChunk, Session, Speaker


class Command(BaseCommand):
    help = "Розгортає базу знань з готового дампу (спікери, сесії, фрагменти з ембедингами)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Замінити поточну базу знань вмістом дампу.",
        )

    def handle(self, *args, **options):
        dump = settings.KNOWLEDGE_DUMP
        if not dump.exists():
            self.stderr.write(f"Немає дампу бази знань {dump}, базу знань не розгорнуто.")
            return
        if not options["force"] and KnowledgeChunk.objects.exists():
            self.stdout.write("База знань уже заповнена, дамп не завантажується.")
            return
        with transaction.atomic():
            KnowledgeChunk.objects.all().delete()
            Session.objects.all().delete()
            Speaker.objects.all().delete()
            call_command("loaddata", str(dump), verbosity=0)
        self.stdout.write(
            self.style.SUCCESS(
                f"Базу знань розгорнуто з {dump.name}: спікерів {Speaker.objects.count()}, "
                f"сесій {Session.objects.count()}, фрагментів {KnowledgeChunk.objects.count()}."
            )
        )
