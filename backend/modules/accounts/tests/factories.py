# AI contribution: 50% or more AI-generated
"""Generated account records for backend tests."""

import factory

from modules.accounts.models import User


class UserFactory(factory.django.DjangoModelFactory):
    """Create distinct synthetic users with passwords hashed by the manager."""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"generated-{n}@example.test")
    first_name = factory.Sequence(lambda n: f"Example{n}")
    last_name = factory.Sequence(lambda n: f"Person{n}")
    password = "local-test-password"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Use create_user so test passwords match production hashing."""
        return model_class.objects.create_user(*args, **kwargs)
