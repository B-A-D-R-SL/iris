# AI contribution: 50% or more AI-generated
"""Explicit email-provider selection shared by HTTP and worker processes."""

from django.conf import settings

from adapters.mailer.base import Mailer, MailerError
from adapters.mailer.fake import get_fake_mailer
from adapters.mailer.smtp import SmtpMailer


def get_mailer() -> Mailer:
    if settings.MAILER_ADAPTER == "smtp":
        return SmtpMailer()
    if settings.MAILER_ADAPTER == "fake":
        return get_fake_mailer()
    if settings.MAILER_ADAPTER == "azure":
        from adapters.mailer.azure import AzureMailer

        return AzureMailer()
    raise MailerError("mailer_not_configured", retryable=False)
