from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.template import loader, TemplateDoesNotExist
import os


def home(request):
    # try to serve frontend/index.html if it exists; otherwise return a minimal OK response
    try:
        template = loader.get_template('index.html')
        return HttpResponse(template.render({}, request))
    except TemplateDoesNotExist:
        return HttpResponse('<html><body><h1>Knowledge Graph Builder</h1></body></html>')


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    # include the Django app using the explicit package path to avoid
    # collisions with the repo-level `ontologies` package
    path('api/', include('django_backend.ontologies.urls')),
]
