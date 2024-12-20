from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Collection, Recipe, Meal, Ingredient, MethodStep, MealPlan, Membership
from .forms import CollectionForm
import requests
from bs4 import BeautifulSoup
from .ai_helpers import parse_recipe_with_genai, summarize_grocery_list_with_genai
from django.views.decorators.http import require_POST
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from django.db import transaction
import logging
from collections import defaultdict
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
# from django.contrib.auth import login

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
    recipe_url = request.POST.get('recipe_url')
    collection_id = request.POST.get('collection_id')
    collection = get_object_or_404(Collection, id=collection_id)
    
    logger.info(f"User {request.user.username} is scraping recipe from URL: {recipe_url}")
    try:
        # Fetch the recipe page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
                            'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                            'Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://www.google.com/',
            'Accept-Language': 'en-US,en;q=0.9',
            #'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        response = requests.get(recipe_url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch the recipe URL: {recipe_url}. Error: {e}")
        messages.error(request, f"Failed to fetch the recipe URL: {e}")
        return redirect('main:collection_detail', pk=collection.id)
    
    # Parse the page content
    soup = BeautifulSoup(response.text, 'html.parser')
    raw_text = soup.get_text(separator='\n')  # Use separator to preserve line breaks
    
    # Parse the raw text into structured data using GenAI
    structured_data = parse_recipe_with_genai(raw_text)
    if not structured_data:
        logger.error(f"Failed to parse the recipe from URL: {recipe_url}")
        messages.error(request, "Failed to parse the recipe. Please try again.")
        return redirect('main:collection_detail', pk=collection.id)
    
    try:
        # Extract Meal information
        meal_title = structured_data.get('title', 'New Meal')
        meal_description = structured_data.get('description', '')
        
        if not meal_title:
            raise ValueError("Meal title is missing in the parsed data.")
        
        # Create the Meal instance
        meal = Meal.objects.create(
            collection=collection,
            title=meal_title,
            description=meal_description,
            url=recipe_url,
        )
        
        logger.info(f"Created Meal: {meal.title} (ID: {meal.id})")
        
        # Iterate over each Recipe in the structured data
        for recipe_data in structured_data.get('recipes', []):
            recipe_title = recipe_data.get('title')
            recipe_description = recipe_data.get('description', '')
            
            if not recipe_title:
                logger.warning("Recipe title is missing. Skipping this recipe.")
                continue  # Skip recipes without a title
            
            # Create the Recipe instance
            recipe = Recipe.objects.create(
                meal=meal,
                title=recipe_title,
                description=recipe_description,
            )
            
            logger.info(f"Created Recipe: {recipe.title} (ID: {recipe.id}) under Meal ID: {meal.id}")
            
            # Iterate over Ingredients
            for ingredient_data in recipe_data.get('ingredients', []):
                ingredient_name = ingredient_data.get('name')
                ingredient_amount = ingredient_data.get('amount')
                ingredient_unit = ingredient_data.get('unit')
                
                if not ingredient_name:
                    logger.warning("Ingredient name is missing. Skipping this ingredient.")
                    continue  # Skip ingredients without a name
                
                # Convert amount to Decimal if possible
                try:
                    # Ensure amount is a string before conversion
                    if isinstance(ingredient_amount, (int, float)):
                        ingredient_amount = str(ingredient_amount)
                    elif not isinstance(ingredient_amount, str):
                        ingredient_amount = ''
                    amount_decimal = Decimal(ingredient_amount)
                except (InvalidOperation, TypeError):
                    amount_decimal = None  # Handle non-numeric amounts like "to taste"
                
                # Create the Ingredient instance
                Ingredient.objects.create(
                    recipe=recipe,
                    name=ingredient_name,
                    amount=amount_decimal,
                    unit=ingredient_unit
                )
                
                logger.info(f"Added Ingredient: {ingredient_name}, Amount: {ingredient_amount}, Unit: {ingredient_unit} to Recipe ID: {recipe.id}")
            
            # Iterate over Method Steps
            for step in recipe_data.get('method', []):
                if not step.strip():
                    logger.warning("Empty method step encountered. Skipping.")
                    continue  # Skip empty steps
                
                # Create the MethodStep instance
                MethodStep.objects.create(
                    recipe=recipe,
                    description=step.strip()
                )
                
                logger.info(f"Added MethodStep to Recipe ID: {recipe.id}: {step.strip()}")
        
        messages.success(request, "Recipe scraped and added to your Cook Book!")
        logger.info(f"Successfully scraped and saved recipe from URL: {recipe_url} for Collection ID: {collection.id}")
    except Exception as e:
        logger.exception(f"An error occurred while saving the recipe from URL: {recipe_url}. Error: {e}")
        messages.error(request, f"An error occurred while saving the recipe: {e}")
        return redirect('main:collection_detail', pk=collection.id)
    
    return redirect('main:meal_detail', pk=meal.id)


@require_POST
@login_required
def generate_grocery_list(request):
    recipe_ids = request.POST.getlist('recipes')
    recipes = Recipe.objects.filter(id__in=recipe_ids, meal__collection__user=request.user)
    ingredients = {}
    for recipe in recipes:
        for ingredient in recipe.ingredients.all():
            key = f"{ingredient.name} ({ingredient.unit})"
            if ingredient.amount is not None:
                try:
                    ingredients[key] = ingredients.get(key, 0) + float(ingredient.amount)
                except ValueError:
                    # Handle cases where amount is not a number
                    if ingredients.get(key):
                        ingredients[key] = ingredients[key]  # Keep existing value
                    else:
                        ingredients[key] = "to taste"
            else:
                ingredients[key] = ingredients.get(key, "to taste")
    context = {'ingredients': ingredients}
    return render(request, 'main/grocery_list.html', context) 

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
        'meal_plan_recipes': [recipe for meal in meal_plan.meals.all() for recipe in meal.recipes.all()],
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
    Redirects back to the originating page.
    """
    meal_plan = latest_meal_plan(request)

    if not meal_plan:
        messages.error(request, "No active meal plan found.")
        return redirect('main:collection_detail', pk=request.GET.get('collection_id'))

    meal = get_object_or_404(Meal, id=meal_id)
    
    if meal_plan.meals.filter(id=meal.id).exists():
        meal_plan.meals.remove(meal)
        messages.info(request, f"'{meal.title}' has been removed from your meal plan.")
    else:
        meal_plan.meals.add(meal)
        messages.success(request, f"'{meal.title}' has been added to your meal plan.")
    
    meal_plan.save()
    
    next_url = request.POST.get('next')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('main:collection_list')))

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
