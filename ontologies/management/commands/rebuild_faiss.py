from django.core.management.base import BaseCommand
import requests
import os


class Command(BaseCommand):
    help = 'Trigger index rebuild. With remote hosting the index is managed externally.'

    def handle(self, *args, **options):
        remote = os.environ.get('REMOTE_INDEX_URL')
        if remote:
            rebuild_url = remote.rstrip('/') + '/rebuild'
            try:
                r = requests.post(rebuild_url, timeout=5)
                if r.status_code == 200:
                    self.stdout.write(self.style.SUCCESS('Remote index rebuild triggered'))
                    return
            except Exception:
                pass
        self.stdout.write('No remote rebuild endpoint available. The project is configured to use a remote HF Space for the index.')
        self.stdout.write('Visit https://huggingface.co/spaces/VivanRajath/Query-chat to manage the index there.')
