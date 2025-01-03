from django.contrib import admin
from .models import (
    Collection,
    Meal,
    Recipe,
    Ingredient,
    MethodStep,
    MealPlan,
    Membership
)

class IngredientInline(admin.TabularInline):
    model = Ingredient
    extra = 1

class MethodStepInline(admin.TabularInline):
    model = MethodStep
    extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [IngredientInline, MethodStepInline]
    list_display = ('title', 'meal')
    search_fields = ('title',)

@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ('title', 'collection')
    search_fields = ('title',)

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user')
    search_fields = ('title', 'user__username')

@admin.register(MethodStep)
class MethodStepAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'description')
    search_fields = ('recipe__title', 'description')

@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'shareable_link')
    search_fields = ('name', 'owner__username', 'shareable_link')
    readonly_fields = ('shareable_link',)

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'meal_plan', 'joined_at')
    search_fields = ('user__username', 'meal_plan__name')
    list_filter = ('meal_plan', 'joined_at') 