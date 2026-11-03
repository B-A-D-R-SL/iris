# AI contribution: 50% or more AI-generated
from django.urls import path

from modules.audit.api.views import AuditSearchView

urlpatterns = [path("", AuditSearchView.as_view(), name="audit-search")]
