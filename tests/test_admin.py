import pytest
from django.contrib import admin
from django.contrib.auth.models import Group, User

from conference.models import ChatLog, KnowledgeChunk, Session, Speaker


@pytest.mark.django_db
def test_admin_manages_knowledge_base_only():
    registered = set(admin.site._registry)
    assert Speaker in registered
    assert Session in registered
    assert KnowledgeChunk in registered
    assert ChatLog not in registered
    assert User not in registered
    assert Group not in registered


@pytest.mark.django_db
def test_admin_changelist_is_the_knowledge_base(client):
    user = User.objects.create_superuser("org", "org@example.com", "pass")
    client.force_login(user)
    assert client.get("/admin/conference/knowledgechunk/").status_code == 200
    assert client.get("/admin/conference/session/").status_code == 200
    assert client.get("/admin/conference/speaker/").status_code == 200
    assert client.get("/admin/conference/chatlog/").status_code == 404
