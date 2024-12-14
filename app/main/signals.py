from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import MealPlan, Membership

@receiver(post_save, sender=User)
def create_user_mealplan(sender, instance, created, **kwargs):
    if created:
        meal_plan = MealPlan.objects.create(
            name=f"{instance.username}'s Meal Plan",
            owner=instance
        )
        Membership.objects.create(
            user=instance,
            meal_plan=meal_plan
        ) 