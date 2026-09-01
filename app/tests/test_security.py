from app.security import API_TOKEN


def test_api_token_has_reasonable_entropy_length():
    assert len(API_TOKEN) >= 32
