# AI contribution: 50% or more AI-generated
"""Reset tests use real allauth, PostgreSQL and the shared fake mail transport."""

import pytest
from django.core.cache import cache

from modules.notifications.tasks import send_email


@pytest.fixture(autouse=True)
def reset_cache(db):
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def queued_reset(notification_rules, monkeypatch):
    jobs = []
    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", lambda **kwargs: jobs.append(kwargs))
    return jobs
