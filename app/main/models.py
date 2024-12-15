from django.db import models
from django.contrib.auth.models import User
from .utils import convert_to_grams
from uuid import uuid4

class Collection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    photo = models.ImageField(upload_to='collection_photos/', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.title



class MealPlan(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, related_name='owned_mealplans', on_delete=models.CASCADE)
    shareable_link = models.UUIDField(default=uuid4, unique=True, editable=False)
    grocery_list = models.TextField(blank=True, null=True)
    grocery_list_instruction = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Meal(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='meals')
    url = models.URLField(null=True, blank=True)
    photo = models.ImageField(upload_to='meal_photos/', null=True, blank=True)
    title = models.CharField(max_length=255)
    meal_plan = models.ManyToManyField(MealPlan, related_name='meals')
    description = models.TextField()

    def __str__(self):
        return self.title

    def in_plan(self, meal_plan):
        if meal_plan:
            return self.meal_plan.filter(id=meal_plan.id).exists()

        return False

class Recipe(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='recipes')
    photo = models.ImageField(upload_to='recipe_photos/', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.title

class Ingredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50)

    def __str__(self):
        if self.amount is not None:
            return f"{self.amount} {self.unit} {self.name}"
        return f"{self.name} ({self.unit})"

    def get_amount_in_grams(self, region='US'):
        if self.amount is not None:
            return convert_to_grams(self.amount, self.unit, region)
        return None

class MethodStep(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='method_steps')
    description = models.TextField()

    def __str__(self):
        return f"Step {self.id}: {self.description[:50]}" 

class Membership(models.Model):
    user = models.ForeignKey(User, related_name='memberships', on_delete=models.CASCADE)
    meal_plan = models.ForeignKey(MealPlan, related_name='memberships', on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'meal_plan')
