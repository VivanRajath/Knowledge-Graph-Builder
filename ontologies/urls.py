from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OntologyViewSet, aggregated_graph, search_graph
from django.http import JsonResponse


def health(request):
    return JsonResponse({'status': 'ok'})

router = DefaultRouter()
router.register(r'ontologies', OntologyViewSet, basename='ontology')

urlpatterns = [
    path('', include(router.urls)),
    path('graph/', aggregated_graph, name='aggregated_graph'),
    path('search_graph/', search_graph, name='search_graph'),
    path('health/', health, name='health'),
]
