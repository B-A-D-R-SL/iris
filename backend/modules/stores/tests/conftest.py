# AI contribution: 50% or more AI-generated
"""Shared admin and invitation-rule fixtures for partner decision workflows."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from modules.accounts.models import User
from modules.accounts.tests.factories import UserFactory
from modules.notifications.tasks import send_email
from modules.rules.models import RuleSetVersion


@pytest.fixture
def admin():
    return UserFactory(role=User.Role.ADMIN)


@pytest.fixture
def invitation_rule(admin):
    return RuleSetVersion.objects.create(
        rule_type="invitations",
        version=1,
        values={"expires_after_days": 7},
        effective_from=timezone.now() - timedelta(days=1),
        created_by=admin,
    )


@pytest.fixture
def partner_origin(settings):
    """Use the same origin contract as notification rendering."""
    settings.PUBLIC_APP_ORIGIN = "https://iris.example"
    return settings.PUBLIC_APP_ORIGIN


@pytest.fixture
def queued_partner_emails(monkeypatch):
    """Capture after-commit work while keeping task execution explicit."""
    queued: list[dict[str, Any]] = []
    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", lambda **kwargs: queued.append(kwargs))
    return queued


@pytest.fixture
def partner_events(caplog, monkeypatch):
    """Capture raw workflow/worker records despite the private root logger."""
    import logging

    loggers = [
        logging.getLogger(name) for name in ("iris.stores", "iris.notifications")
    ]
    for logger in loggers:
        monkeypatch.setattr(logger, "propagate", False)
        logger.addHandler(caplog.handler)
        caplog.set_level(logging.INFO, logger=logger.name)
    try:
        yield caplog
    finally:
        for logger in loggers:
            logger.removeHandler(caplog.handler)
