def test_erroneous_json(mocked_client):
    response = mocked_client.post('/ndvi/raster', json={})

    assert response.status_code == 422
