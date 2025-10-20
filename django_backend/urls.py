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
    path('api/', include('ontologies.urls')),
]
