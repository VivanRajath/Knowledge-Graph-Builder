from django.db import models

class Ontology(models.Model):
    filename = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=255, blank=True)
    json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} ({self.created_at.isoformat()})"
