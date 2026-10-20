from django.contrib import admin
from django.urls import path

from assistant.views import chat

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", chat, name="chat"),
]
