from django.test import Client


def test_health_endpoint():
    c = Client()
    resp = c.get('/api/health/')
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('status') == 'ok'
