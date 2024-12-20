from django.db import migrations

def fix_none_strings(apps, schema_editor):
    MealPlan = apps.get_model('main', 'MealPlan')
    for meal_plan in MealPlan.objects.all():
        if meal_plan.grocery_list_instruction == 'None':
            meal_plan.grocery_list_instruction = ''
            meal_plan.save()

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_mealplan_grocery_list_instruction'),  # Replace with your last migration
    ]

    operations = [
        migrations.RunPython(fix_none_strings),
    ]
