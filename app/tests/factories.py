# tests/factories.py
import factory
from django.contrib.auth.models import User
from main.models import Collection, MealPlan, Membership

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True  # Prevents the automatic save after set_password

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall('set_password', 'password123')
    is_staff = False
    is_superuser = False
    is_active = True

    @factory.post_generation
    def password_save(obj, create, extracted, **kwargs):
        if create:
            obj.save()

class CollectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Collection
    
    user = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Collection {n}")
    description = factory.Faker('paragraph')

class MealPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MealPlan
    
    name = factory.Sequence(lambda n: f"Meal Plan {n}")
    owner = factory.SubFactory(UserFactory)

class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership
    
    user = factory.SubFactory(UserFactory)
    meal_plan = factory.SubFactory(MealPlanFactory)