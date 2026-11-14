# AI contribution: 50% or more AI-generated
"""Notice file routes, mounted at /api/staff/."""

from django.urls import path

from modules.documents.api.views import NoticeFileDownloadView, NoticeFileLinkView

urlpatterns = [
    path(
        "notices/<uuid:id>/file/",
        NoticeFileLinkView.as_view(),
        name="staff-notice-file-link",
    ),
    path(
        "notice-files/<str:token>/",
        NoticeFileDownloadView.as_view(),
        name="staff-notice-file-download",
    ),
]
