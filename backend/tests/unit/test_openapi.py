from fastapi.testclient import TestClient

from app.main import app


def test_root_redirects_to_swagger_ui() -> None:
    client = TestClient(app, follow_redirects=False)

    response = client.get("/")

    assert response.status_code == 307
    assert response.headers["location"] == "/swagger.html"

    legacy_response = client.get("/docs")
    assert legacy_response.status_code == 307
    assert legacy_response.headers["location"] == "/swagger.html"


def test_swagger_and_openapi_expose_api_key_authorization() -> None:
    client = TestClient(app)

    docs = client.get("/swagger.html")
    schema_response = client.get("/openapi.json")

    assert docs.status_code == 200
    assert "Swagger UI" in docs.text
    assert '"persistAuthorization": true' in docs.text
    schema = schema_response.json()
    assert schema["components"]["securitySchemes"]["ApiKeyAuth"] == {
        "type": "apiKey",
        "description": "API key configured in API_KEYS_JSON. Optional when AUTH_MODE=disabled.",
        "in": "header",
        "name": "X-API-Key",
    }
    assert {"ApiKeyAuth": []} in schema["paths"]["/api/v1/results"]["post"]["security"]
    assert {"ApiKeyAuth": []} in schema["paths"]["/api/v1/submissions"]["post"]["security"]
    examples = schema["components"]["schemas"]["ResultCreate"]["examples"]
    assert schema["components"]["schemas"]["ResultCreate"]["required"] == [
        "file_name",
        "query_content",
        "img_id",
        "video_id",
        "submitter",
    ]
    assert {example["file_name"] for example in examples} == {
        "query-p1-1-kis",
        "query-p1-2-qa",
        "query-p1-3-trake",
    }
    assert all(example["query_content"] for example in examples)
