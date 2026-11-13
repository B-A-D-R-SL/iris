# AI contribution: 50% or more AI-generated
"""SMTP callbacks have a finite deadline, including in production settings."""

import json
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf", "2.5"])
def test_smtp_timeout_requires_a_finite_positive_deadline(timeout):
    """Bad settings fail at startup; valid values reach the SMTP connection."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; from django.conf import settings; "
                "print(json.dumps(settings.MAILERS['default']['OPTIONS']['timeout']))"
            ),
        ],
        env={
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "iris.settings.test",
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "SMTP_TIMEOUT": timeout,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if timeout == "2.5":
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == 2.5
    else:
        assert result.returncode != 0
        assert "SMTP_TIMEOUT must be finite and positive." in result.stderr
