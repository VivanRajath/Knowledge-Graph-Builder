from django.contrib import admin
from .models import Ontology

@admin.register(Ontology)
class OntologyAdmin(admin.ModelAdmin):
    list_display = ('id', 'filename', 'source', 'created_at')
    readonly_fields = ('created_at',)
