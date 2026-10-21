# AI contribution: 50% or more AI-generated
"""Verify the served OpenAPI contract without changing application endpoints."""

import json

from django.test import Client
from django.urls import reverse
from drf_spectacular.validation import validate_schema
from jsonschema import validate


def test_schema_serves_valid_openapi(client: Client) -> None:
    response = client.get(
        reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json"
    )

    assert response.status_code == 200
    schema = json.loads(response.content)
    validate_schema(schema)
    assert reverse("health") in schema["paths"]


def test_health_response_matches_public_openapi_contract(client: Client) -> None:
    schema_response = client.get(
        reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json"
    )
    schema = json.loads(schema_response.content)
    operation = schema["paths"][reverse("health")]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]

    response = client.get(reverse("health"), HTTP_ACCEPT="text/html")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert operation["security"] == []
    assert response_schema["required"] == ["status"]
    assert response_schema["properties"]["status"]["enum"] == ["ok"]
    validate(instance=response.json(), schema=response_schema)


def test_docs_remains_accessible_and_points_to_schema(client: Client) -> None:
    assert reverse("swagger-ui") == "/api/docs/"

    response = client.get(reverse("swagger-ui"))

    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]
    assert reverse("schema").encode() in response.content
    assert b"SwaggerUIBundle" in response.content


def test_health_still_rejects_post(client: Client) -> None:
    response = client.post(reverse("health"), data={})

    assert response.status_code == 405
    assert response["Allow"] == "GET"
