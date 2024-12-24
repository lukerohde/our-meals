from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Collection, Recipe, Meal, Ingredient, MethodStep, MealPlan, Membership
from .forms import CollectionForm
import requests
from bs4 import BeautifulSoup
from .ai_helpers import scrape_recipe_from_url, summarize_grocery_list_with_genai
from django.views.decorators.http import require_POST
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from django.db import transaction
import logging
from collections import defaultdict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.urls import reverse
from django.template.loader import render_to_string

# Configure logger
logger = logging.getLogger(__name__)

def get_possessive_name(name):
    """Returns the possessive form of a name, handling 's' endings correctly."""
    return f"{name}'" if name.endswith('s') else f"{name}'s"

# @login_required
# def collection_list(request):
#     collections = Collection.objects.filter(user=request.user)
#     return render(request, 'main/collection_list copy.html', {'collections': collections})

def latest_meal_plan(request):
    latest_membership = request.user.memberships.order_by('-joined_at').first()
    latest_meal_plan = latest_membership.meal_plan if latest_membership else None
    return latest_meal_plan

@login_required
def collection_list(request):
    meal_plan = latest_meal_plan(request)
    
    if meal_plan:
        # Get members of the latest meal plan excluding the current user
        members = Membership.objects.filter(meal_plan=meal_plan).exclude(user=request.user).select_related('user')
        
        # Get collections of all members
        member_collections = Collection.objects.filter(user__in=[membership.user for membership in members])
    else:
        members = []
        member_collections = Collection.objects.none()
    
    # Group collections by owner with additional member info
    grouped_collections = {}
    
    # Add user's own collections first
    grouped_collections['Your Cook Books'] = {
        'collections': Collection.objects.filter(user=request.user),
        'member_id': None
    }
    
    # Add collections from meal plan members
    for membership in members:
        grouped_collections[f"{get_possessive_name(membership.user.username.title())} Cook Books"] = {
            'collections': Collection.objects.filter(user=membership.user),
            'member_id': membership.user.id
        }
    
    context = {
        'grouped_collections': grouped_collections,
        'meal_plan': meal_plan,
    }
    
    return render(request, 'main/collection_list_grouped.html', context)

@login_required
def collection_create(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST, request.FILES)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.user = request.user
            collection.save()
            return redirect('main:collection_list')
    else:
        form = CollectionForm()
    return render(request, 'main/collection_form.html', {'form': form})

@require_POST
@login_required
@transaction.atomic
def scrape_recipe(request):
    """
    Scrape a recipe from a URL and create a new meal with recipes.
    Supports both AJAX and regular form submissions for progressive enhancement.
    """    
    recipe_url = request.POST.get('recipe_url')
    collection_id = request.POST.get('collection_id')
    collection = get_object_or_404(Collection, id=collection_id)
    
    logger.info(f"User {request.user.username} is scraping recipe from URL: {recipe_url}")
    
    try:
        structured_data = scrape_recipe_from_url(recipe_url)
        
        # Create the meal
        meal = Meal.objects.create(
            title=structured_data.get('title', 'New Meal'),
            collection=collection,
            description=structured_data.get('description', ''),
            url=recipe_url
        )
        
        logger.info(f"Created Meal: {meal.title} (ID: {meal.id})")
        
        # Create recipes and their components
        for recipe_data in structured_data.get('recipes', []):
            recipe = Recipe.objects.create(
                meal=meal,
                title=recipe_data.get('title', ''),
                description=recipe_data.get('description', ''),
            )
            
            # Create ingredients
            for ingredient in recipe_data.get('ingredients', []):
                Ingredient.objects.create(
                    recipe=recipe,
                    name=ingredient.get('name', ''),
                    amount=ingredient.get('amount', None),
                    unit=ingredient.get('unit', '')
                )
            
            # Create method steps
            for step in recipe_data.get('method', []):
                MethodStep.objects.create(
                    recipe=recipe,
                    description=step.strip()
                )
        
        messages.success(request, "Recipe successfully imported!")
        redirect_url = reverse('main:meal_detail', args=[meal.id])
        
        # Check if this is an AJAX request
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'status': 'success',
                'redirect': redirect_url
            })
        
        # Regular form submission
        return redirect(redirect_url)
            
    except ValueError as e:
        # Handle specific scraping errors
        logger.warning(f"Failed to scrape recipe from {recipe_url}: {str(e)}")
        error_message = str(e)
        if "Failed to fetch" in error_message:
            error_message = "We couldn't access that website. Please check the URL and try again."
        
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'status': 'error',
                'message': error_message
            }, status=400)
        
        messages.error(request, error_message)
        return redirect('main:collection_detail', pk=collection.id)
            
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error processing recipe from {recipe_url}: {str(e)}")
        error_message = "An unexpected error occurred. Please try again later."
        
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'status': 'error',
                'message': error_message
            }, status=500)
        
        messages.error(request, error_message)
        return redirect('main:collection_detail', pk=collection.id)


@login_required
def collection_detail(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    
    meal_plan = latest_meal_plan(request)
    meal_plan_recipes = meal_plan.meals.values_list('id', flat=True) if meal_plan else []

    context = {
        'collection': collection,
        'meal_plan_recipes': meal_plan_recipes
    }
    
    return render(request, 'main/collection_detail.html', context)

@login_required
def meal_detail(request, pk):
    """
    Display the details of a specific Meal, including its Recipes.
    
    Parameters:
        request (HttpRequest): The HTTP request object.
        pk (int): The primary key of the Meal.
        
    Returns:
        HttpResponse: Rendered meal_detail.html template.
    """
    meal = get_object_or_404(Meal, pk=pk)
    recipes = meal.recipes.all()
    
    # Get meal plan info
    meal_plan = latest_meal_plan(request)
    meal_plan_recipes = meal_plan.meals.values_list('id', flat=True) if meal_plan else []
    
    context = {
        'meal': meal,
        'recipes': recipes,
        'meal_plan_recipes': meal_plan_recipes,
    }
    
    return render(request, 'main/meal_detail.html', context)

def meal_plan_detail(request, shareable_link):
    """
    Display a meal plan based on the shareable link. Accessible to both authenticated members and unauthenticated users.
    """
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    
    # Get all members except the owner
    other_members = meal_plan.memberships.exclude(user=meal_plan.owner)
    all_members = [m.user for m in meal_plan.memberships.all()]
    

    context = {
        'meal_plan': meal_plan,
        'is_member': request.user.is_authenticated and (
            meal_plan.owner == request.user or 
            meal_plan.memberships.filter(user=request.user).exists()
        ),
        'meal_plan_recipes': [meal.id for meal in meal_plan.meals.all()],
        'other_members': other_members,
        'all_members': all_members,
    }
    
    return render(request, 'main/meal_plan_detail.html', context)

def join_meal_plan(request, shareable_link):
    if request.user.is_authenticated:
        # Existing code for authenticated users
        meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
        
        if Membership.objects.filter(user=request.user, meal_plan=meal_plan).exists():
            messages.error(request, "You are already a member of this meal plan.")
            return redirect('main:meal_plan_detail', shareable_link=shareable_link)
        
        Membership.objects.create(user=request.user, meal_plan=meal_plan)
        messages.success(request, f"You have successfully joined the meal plan '{meal_plan.name}'.")
        return redirect('main:meal_plan_detail', shareable_link=shareable_link)
    else:
        # Handle unauthenticated users
        request.session['joining_shareable_link'] = shareable_link
        messages.info(request, "Please sign up to join the meal plan.")
        return redirect('account_signup')  # Ensure you have a URL named 'signup'

@login_required
def leave_meal_plan(request, shareable_link):
    """
    Allow a user to leave their current meal plan.
    """
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    if request.user == meal_plan.owner:
        messages.error(request, "Owners cannot leave their own meal plan.")
        return redirect('main:meal_plan_detail', shareable_link=shareable_link)
    
    membership = Membership.objects.filter(user=request.user, meal_plan=meal_plan).first()
    if membership:
        membership.delete()
        messages.success(request, f"You have left the meal plan '{meal_plan.name}'.")
    else:
        messages.error(request, "You are not a member of this meal plan.")
    
    return redirect('main:collection_list')

@require_POST
@login_required
def toggle_meal_in_meal_plan(request, meal_id):
    """
    Adds or removes a meal from the user's latest meal plan.
    Handles both AJAX and regular form submissions.
    """
    meal = get_object_or_404(Meal, id=meal_id)
    meal_plan = latest_meal_plan(request)
    collection_id = request.GET.get('collection_id')
    
    if meal in meal_plan.meals.all():
        meal_plan.meals.remove(meal)
        message = f"{meal.title} removed from meal plan!"
    else:
        meal_plan.meals.add(meal)
        message = f"{meal.title} added to meal plan!"
    
    messages.success(request, message)
    
    if request.headers.get('HX-Request'):
        # For AJAX requests, render just the meal partial
        collection = get_object_or_404(Collection, id=collection_id) if collection_id else None
        meal_plan_recipes = set(meal_plan.meals.values_list('id', flat=True))
        context = {
            'meal': meal,
            'show_buttons': True,
            'collection': collection,
            'meal_plan_recipes': meal_plan_recipes
        }
        html = render_to_string('main/_meal.html', context, request)
        return JsonResponse({
            'html': html,
            'message': message
        })
    
    # For regular form submissions, redirect back to the referring page
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@require_POST
@login_required
def delete_meal(request, meal_id):
    meal = get_object_or_404(Meal, id=meal_id)
    collection = meal.collection
    meal.delete()
    return redirect('main:collection_detail', pk=collection.id)

@require_POST
@login_required
def create_grocery_list(request, shareable_link):
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    ingredients = gather_ingredients(meal_plan)
    grocery_list_instruction = request.POST.get('grocery_list_instruction', '') or ''
    formatted_list = summarize_grocery_list_with_genai(ingredients, grocery_list_instruction)
    meal_plan.grocery_list = formatted_list
    meal_plan.grocery_list_instruction = grocery_list_instruction
    meal_plan.save()
    return redirect('main:meal_plan_detail', shareable_link=shareable_link)

@require_POST
@login_required
def save_grocery_list(request, shareable_link):
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    meal_plan.grocery_list = request.POST.get('grocery_list', '')
    meal_plan.save()
    return JsonResponse({'status': 'success'})

def gather_ingredients(meal_plan):
    ingredients = []
    for meal in meal_plan.meals.all():
        for recipe in meal.recipes.all():
            ingredients.extend(recipe.ingredients.all())
    return ingredients

@login_required
def meal_plan_edit(request, shareable_link):
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    
    # Only the owner can edit the meal plan
    if request.user != meal_plan.owner:
        messages.error(request, "You don't have permission to edit this meal plan.")
        return redirect('main:meal_plan_detail', shareable_link=shareable_link)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            meal_plan.name = name
            meal_plan.save()
            messages.success(request, 'Meal plan updated successfully!')
            return redirect('main:meal_plan_detail', shareable_link=shareable_link)
        else:
            messages.error(request, 'Please provide a name for your meal plan.')
    
    return render(request, 'main/meal_plan_form.html', {'meal_plan': meal_plan})

@login_required
def remove_member(request, shareable_link, member_id):
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    if request.user != meal_plan.owner:
        return HttpResponseForbidden("Only the meal plan owner can remove members")
    
    member = get_object_or_404(User, id=member_id)
    Membership.objects.filter(user=member, meal_plan=meal_plan).delete()
    messages.success(request, f"Removed {member.username} from your meal plan")
    return redirect('main:collection_list')
