# AI contribution: 50% or more AI-generated

import pytest
from django.utils.translation import override

from modules.households.models import Household


@pytest.mark.parametrize(
    ("status", "label"),
    [
        (Household.Status.REVIEW_REQUIRED, "Vérification par l'équipe requise"),
        (Household.Status.AWAITING_VISIT, "Visite en personne requise"),
        (Household.Status.RENEWAL_NEEDED, "Renouvellement requis"),
    ],
)
def test_french_status_labels(status, label):
    with override("fr"):
        assert Household(status=status).get_status_display() == label
