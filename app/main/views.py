from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.contrib import messages
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.template.loader import render_to_string
from django.middleware.csrf import get_token
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
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import reverse
from django.template.loader import render_to_string
from django.db.models import Count, Q

# Configure logger
logger = logging.getLogger(__name__)

def get_possessive_name(name):
    """Convert a name to its possessive form."""
    if name.endswith('s'):
        return f"{name}'"
    return f"{name}'s"

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
    # Get all meal plans where the user is a member
    user_meal_plans = MealPlan.objects.filter(memberships__user=request.user)
    
    # Get all users who share any meal plan with the current user
    shared_users = User.objects.filter(
        memberships__meal_plan__in=user_meal_plans
    ).distinct().exclude(id=request.user.id)
    
    # Get the latest meal plan for member removal context
    meal_plan = latest_meal_plan(request)
    
    # Group collections by owner with additional member info
    grouped_collections = {}
    
    # Add user's own collections first
    grouped_collections['Your Cook Books'] = {
        'collections': Collection.objects.filter(user=request.user),
        'member_id': None
    }
    
    # Add collections from users who share any meal plan
    for shared_user in shared_users:
        grouped_collections[f"{get_possessive_name(shared_user.username.title())} Cook Books"] = {
            'collections': Collection.objects.filter(user=shared_user),
            'member_id': shared_user.id
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
def scrape_recipe(request, collection_id):
    """
    Scrape a recipe from a URL and create a new meal with recipes.
    Supports both AJAX and regular form submissions for progressive enhancement.
    """
    recipe_url = request.POST.get('recipe_url')
    collection = get_object_or_404(Collection, id=collection_id)
    
    logger.info(f"User {request.user.username} is scraping recipe from URL: {recipe_url}")
    
    try:
        structured_data = scrape_recipe_from_url(recipe_url)
        structured_data['url'] = recipe_url  # Add URL to structured data
        
        # Create meal using helper function
        meal = create_meal_from_data(structured_data, collection)
        logger.info(f"Created Meal: {meal.title} (ID: {meal.id})")
        
        messages.success(request, "Recipe successfully imported!")
        redirect_url = reverse('main:meal_detail', args=[meal.id])
        
        # Check if this is an AJAX request
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'status': 'success',
                'message': 'Recipe successfully imported!',
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
    
    # Check if user owns the collection or shares any meal plan with the collection owner
    if collection.user != request.user:
        # Get all meal plans where both users are members
        shared_meal_plans = MealPlan.objects.filter(
            memberships__user__in=[request.user, collection.user]
        ).annotate(
            member_count=Count('memberships__user', distinct=True)
        ).filter(member_count=2).exists()
        
        if not shared_meal_plans:
            raise Http404("Collection not found")
    
    meal_plan = latest_meal_plan(request)
    meal_plan_recipes = meal_plan.meals.values_list('id', flat=True) if meal_plan else []

    context = {
        'collection': collection,
        'meal_plan_recipes': meal_plan_recipes,
        'current_meal_plan': meal_plan,
    }
    
    return render(request, 'main/collection_detail.html', context)

@login_required
def meal_detail(request, pk):
    """
    Display the details of a specific Meal, including its Recipes.
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
        'current_meal_plan': meal_plan,
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
        'current_meal_plan': meal_plan,
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
        # Handle unauthenticated users - convert UUID to string for session storage
        request.session['joining_shareable_link'] = str(shareable_link)
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
def toggle_meal_in_meal_plan(request, shareable_link, meal_id):
    """
    Add or remove a meal from a meal plan.
    """
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    meal = get_object_or_404(Meal, id=meal_id)
    
    # Check if user is a member of the meal plan
    if not meal_plan.memberships.filter(user=request.user).exists():
        raise Http404("Meal plan not found")
    
    # Check if user has access to the meal through shared meal plans
    if meal.collection.user != request.user:
        shared_meal_plans = MealPlan.objects.filter(
            memberships__user__in=[request.user, meal.collection.user]
        ).annotate(
            member_count=Count('memberships__user', distinct=True)
        ).filter(member_count=2).exists()
        
        if not shared_meal_plans:
            raise Http404("Meal not found")
    
    # Toggle meal in meal plan
    if meal in meal_plan.meals.all():
        meal_plan.meals.remove(meal)
        message = f"{meal.title} removed from meal plan!"
        status = 'success'
    else:
        meal_plan.meals.add(meal)
        message = f"{meal.title} added to meal plan!"
        status = 'success'
    
    # Handle AJAX requests
    if request.headers.get('Accept') == 'application/json':
        context = { 
            'meal': meal,
            'meal_plan_recipes': meal_plan.meals.values_list('id', flat=True),
            'current_meal_plan': meal_plan,
            'show_buttons': True,
        }
        html = render_to_string('main/_meal.html', context, request)
        return JsonResponse({
            'message': message,
            'status': status,
            'html': html
        })
    
    # Handle regular form submissions
    messages.success(request, message)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

@require_POST
@login_required
def delete_meal(request, pk):
    """
    Delete a meal and handle both AJAX and regular form submissions.
    For meal plan page, removes the meal card. For collection page, redirects.
    """
    meal = get_object_or_404(Meal, pk=pk)
    
    # Check if user owns the meal's collection
    if meal.collection.user != request.user:
        raise Http404("Meal not found")
    
    # Store message before deleting
    message = f"{meal.title} has been deleted!"
    
    # Delete the meal
    meal.delete()
    
    # Handle AJAX requests
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'message': message,
            'status': 'success'
        })
    
    # For regular form submissions, show message and redirect
    messages.success(request, message)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

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
    membership = get_object_or_404(Membership, user=member, meal_plan=meal_plan)
    membership.delete()
    messages.success(request, f"Removed {member.username} from your meal plan")
    return redirect('main:collection_list')

def create_meal_from_data(structured_data, collection):
    meal = Meal.objects.create(
        title=structured_data.get('title', 'New Meal'),
        collection=collection,
        description=structured_data.get('description', ''),
        url=structured_data.get('url', '')
    )
    
    for recipe_data in structured_data.get('recipes', []):
        recipe = Recipe.objects.create(
            meal=meal,
            title=recipe_data.get('title', ''),
            description=recipe_data.get('description', ''),
        )
        
        for ingredient in recipe_data.get('ingredients', []):
            Ingredient.objects.create(
                recipe=recipe,
                name=ingredient.get('name', ''),
                amount=ingredient.get('amount', None),
                unit=ingredient.get('unit', '')
            )
        
        for step in recipe_data.get('method', []):
            MethodStep.objects.create(
                recipe=recipe,
                description=step.strip()
            )
    
    return meal
