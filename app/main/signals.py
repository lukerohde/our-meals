from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
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

@receiver(user_logged_in, sender=User)
def join_meal_plan_on_login(sender, request, user, **kwargs):
    shareable_link = request.session.pop('joining_shareable_link', None)
    if shareable_link:
        meal_plan = MealPlan.objects.filter(shareable_link=shareable_link).first()
        if meal_plan and not Membership.objects.filter(user=user, meal_plan=meal_plan).exists():
            Membership.objects.create(user=user, meal_plan=meal_plan)
            messages.success(request, f"You have successfully joined the meal plan '{meal_plan.name}'.")
            return redirect('main:meal_plan_detail', shareable_link=shareable_link) 