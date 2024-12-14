from django.db import migrations

def create_default_mealplans(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    MealPlan = apps.get_model('main', 'MealPlan')
    Membership = apps.get_model('main', 'Membership')
    import uuid

    for user in User.objects.all():
        if not MealPlan.objects.filter(owner=user).exists():
            meal_plan = MealPlan.objects.create(
                name=f"{user.username}'s Meal Plan",
                owner=user,
                shareable_link=str(uuid.uuid4())  # Ensure unique shareable_link
            )
            Membership.objects.create(
                user=user,
                meal_plan=meal_plan
            )

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_mealplan_membership'),
    ]

    operations = [
        migrations.RunPython(create_default_mealplans),
    ] 