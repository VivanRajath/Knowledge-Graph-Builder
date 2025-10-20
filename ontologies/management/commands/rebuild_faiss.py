from django.core.management.base import BaseCommand
from ontologies.faiss_index import build_index


class Command(BaseCommand):
    help = 'Rebuild FAISS index from Ontology records'

    def handle(self, *args, **options):
        build_index()
        self.stdout.write(self.style.SUCCESS('FAISS index rebuilt'))
