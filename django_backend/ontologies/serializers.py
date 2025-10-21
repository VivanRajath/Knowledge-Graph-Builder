from rest_framework import serializers
from .models import Ontology

class OntologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ontology
        fields = ['id', 'filename', 'source', 'json', 'created_at']
