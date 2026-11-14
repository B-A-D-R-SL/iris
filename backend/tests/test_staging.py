# AI contribution: 50% or more AI-generated
"""SET-17: preserve API errors, fail readiness safely and serialize staging setup."""

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError

from iris.management.commands import prepare_staging
from tests.test_production_settings import _run


@pytest.fixture
def release_settings(settings, tmp_path):
    settings.ROOT_URLCONF = "iris.staging_urls"
    settings.BASE_DIR = tmp_path
    root = tmp_path / "frontend_dist"
    root.mkdir()
    (root / "index.html").write_text("<html>fictional release</html>")
    return settings


@pytest.mark.parametrize("path", ["/", "/sign-in", "/staff/walk-in/fictional"])
def test_spa_deep_links_are_not_cached(client, release_settings, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"<html>fictional release</html>"
    assert "no-store" in response["Cache-Control"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/not-real",
        "/admin/not-real",
        "/accounts/not-real",
        "/static/missing.css",
        "/assets/missing.js",
        "/missing.js",
        "/api",
    ],
)
def test_backend_and_missing_assets_never_return_spa(client, release_settings, path):
    response = client.get(path)
    assert response.status_code in {301, 302, 404}
    assert b"fictional release" not in response.content


def test_spa_refuses_post_and_missing_build(client, release_settings):
    assert client.post("/sign-in").status_code == 405
    (release_settings.BASE_DIR / "frontend_dist" / "index.html").unlink()
    assert client.get("/sign-in").status_code == 404


@pytest.mark.parametrize(
    "name",
    [
        "DJANGO_SECRET_KEY",
        "SEED_PASSWORD",
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_COMMUNICATION_CONNECTION_STRING",
    ],
)
def test_staging_refuses_unresolved_vault_references(name):
    result = _run(
        ["-c", "import iris.settings.staging"],
        DJANGO_SETTINGS_MODULE="iris.settings.staging",
        **{
            name: "@Microsoft.KeyVault(SecretUri=https://example.vault.azure.net/secrets/test/)"
        },
    )
    assert result.returncode != 0
    assert f"{name} Key Vault reference must resolve." in result.stderr


@pytest.mark.django_db
def test_readiness_identifies_the_running_revision(
    client, release_settings, tmp_path, monkeypatch
):
    pid_file = tmp_path / "worker.pid"
    pid_file.write_text("12345")
    monkeypatch.setenv("IRIS_RELEASE_SHA", "a" * 40)
    with (
        patch("iris.staging_views.WORKER_PID_FILE", pid_file),
        patch("iris.staging_views.os.kill") as kill,
    ):
        response = client.get("/api/ready/")
    kill.assert_called_once_with(12345, 0)
    assert response.json() == {"status": "ok", "revision": "a" * 40}
    assert "no-store" in response["Cache-Control"]


@pytest.mark.parametrize("pid", ["", "0", "-1", "not-a-pid", "12345"])
def test_readiness_refuses_missing_or_dead_worker(
    client, release_settings, tmp_path, pid
):
    pid_file = tmp_path / "worker.pid"
    pid_file.write_text(pid)
    with (
        patch("iris.staging_views.WORKER_PID_FILE", pid_file),
        patch("iris.staging_views.os.kill", side_effect=ProcessLookupError),
    ):
        response = client.get("/api/ready/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_readiness_does_not_expose_database_errors(client, release_settings, tmp_path):
    pid_file = tmp_path / "worker.pid"
    pid_file.write_text("12345")
    with (
        patch("iris.staging_views.WORKER_PID_FILE", pid_file),
        patch("iris.staging_views.os.kill"),
        patch(
            "iris.staging_views.connection.cursor",
            side_effect=DatabaseError("private connection secret"),
        ),
    ):
        response = client.get("/api/ready/")
    assert response.status_code == 503
    assert b"private connection secret" not in response.content


@pytest.mark.parametrize(
    "seed,expected", [("0", ["check", "migrate"]), ("1", ["check", "migrate", "seed"])]
)
def test_prepare_staging_migrates_then_optionally_seeds(
    settings, monkeypatch, seed, expected
):
    settings.SETTINGS_MODULE = "iris.settings.staging"
    monkeypatch.setenv("IRIS_SEED_ON_START", seed)
    monkeypatch.setenv("SEED_PASSWORD", "fictional-test-password")
    with (
        patch.object(prepare_staging, "connection") as connection,
        patch.object(prepare_staging, "call_command") as command,
    ):
        call_command("prepare_staging")
    assert [call.args[0] for call in command.call_args_list] == expected
    sql = connection.cursor.return_value.__enter__.return_value.execute.call_args_list
    assert sql[0].args == ("SELECT pg_advisory_lock(%s)", [408_017])
    assert sql[-1].args == ("SELECT pg_advisory_unlock(%s)", [408_017])


def test_prepare_staging_unlocks_and_does_not_seed_failed_migration(
    settings, monkeypatch
):
    settings.SETTINGS_MODULE = "iris.settings.staging"
    monkeypatch.setenv("IRIS_SEED_ON_START", "1")
    monkeypatch.setenv("SEED_PASSWORD", "fictional-test-password")
    with (
        patch.object(prepare_staging, "connection") as connection,
        patch.object(
            prepare_staging,
            "call_command",
            side_effect=[None, CommandError("migration failed")],
        ) as command,
        pytest.raises(CommandError, match="migration failed"),
    ):
        call_command("prepare_staging")
    assert [call.args[0] for call in command.call_args_list] == ["check", "migrate"]
    sql = connection.cursor.return_value.__enter__.return_value.execute.call_args_list
    assert sql[-1].args[0] == "SELECT pg_advisory_unlock(%s)"


@pytest.mark.parametrize(
    "module,seed,password",
    [
        ("iris.settings.production", "1", "test"),
        ("iris.settings.staging", "yes", "test"),
        ("iris.settings.staging", "1", ""),
    ],
)
def test_prepare_staging_refuses_bad_config_before_writes(
    settings, monkeypatch, module, seed, password
):
    settings.SETTINGS_MODULE = module
    monkeypatch.setenv("IRIS_SEED_ON_START", seed)
    monkeypatch.setenv("SEED_PASSWORD", password)
    with (
        patch.object(prepare_staging, "connection") as connection,
        pytest.raises(CommandError),
    ):
        call_command("prepare_staging")
    connection.cursor.assert_not_called()
