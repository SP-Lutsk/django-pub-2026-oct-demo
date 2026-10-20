import pytest


@pytest.mark.django_db
def test_chat_page_renders_quick_prompts(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "Що розказував Влад?" in body
    assert "Хто розповідав про NumPy?" in body
    assert "Яка погода в Луцьку?" in body
    assert "ws/chat/" in body
    assert 'data-mode' in body
    assert 'id="question"' in body
    assert "AI-асистент заходу" in body
    assert "технічна глибина стеку" in body
    assert "Як винести інференс PyTorch у Celery?" in body
    assert "Джерела" not in body
    assert 'class="composer-shell"' in body
