# AI contribution: 50% or more AI-generated
"""Reusable Listing records for tests in listings and dependent modules."""

from datetime import timedelta
from itertools import count

import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.utils import timezone

from modules.categories.tests.factories import CategoryFactory
from modules.listings.models import Listing
from modules.stores.tests.factories import StoreFactory

_staff_numbers = count()


def create_staff_user() -> AbstractBaseUser:
    """Create a user who posts listings, whichever user model is active.

    Uses the model's sign-in field so it works with Django's default user
    (username) and with the accounts.User model from US-01 (email). Replace with
    the accounts user factory once it exists.
    """
    user_model = get_user_model()
    sign_in = f"listing-staff-{next(_staff_numbers)}@example.test"
    return user_model._default_manager.create_user(
        **{user_model.USERNAME_FIELD: sign_in}, password=None
    )


class ListingFactory(factory.django.DjangoModelFactory):
    """Build a valid published food listing with a two-hour pickup tomorrow."""

    class Meta:
        model = Listing

    store = factory.SubFactory(StoreFactory)
    category = factory.SubFactory(CategoryFactory)
    title = factory.Sequence(lambda n: f"Pains de la veille {n}")
    quantity_total = 10
    pickup_start = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))
    pickup_end = factory.LazyAttribute(lambda o: o.pickup_start + timedelta(hours=2))
    best_before = factory.LazyAttribute(lambda o: timezone.localdate(o.pickup_end))
    created_by = factory.LazyFunction(create_staff_user)
    safe_confirmed_by = factory.SelfAttribute("created_by")
    safe_confirmed_at = factory.LazyFunction(timezone.now)
    published_at = factory.SelfAttribute("safe_confirmed_at")
