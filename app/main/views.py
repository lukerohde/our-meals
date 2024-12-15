from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
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
from django.http import HttpResponseRedirect
from django.urls import reverse

# Configure logger
logger = logging.getLogger(__name__)


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
    # import ipdb; ipdb.set_trace()
    # collections = Collection.objects.filter(user=request.user)
    # return render(request, 'main/collection_list.html', {'collections': collections})

    if latest_meal_plan(request):
        # Get members of the latest meal plan excluding the current user
        members = Membership.objects.filter(meal_plan=latest_meal_plan(request)).exclude(user=request.user).select_related('user')
        
        # Get collections of all members
        member_collections = Collection.objects.filter(user__in=[membership.user for membership in members])
    else:
        member_collections = Collection.objects.none()
    
    # Group collections by owner
    grouped_collections = {}
    
    # Add user's own collections first
    grouped_collections['You'] = Collection.objects.filter(user=request.user)
    
    # Add collections from meal plan members
    for membership in members:
        grouped_collections[membership.user.username] = Collection.objects.filter(user=membership.user)
    
    result = render(request, 'main/collection_list_grouped.html', {'grouped_collections': grouped_collections})
    return result

@login_required
def collection_create(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST, request.FILES)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.user = request.user
            collection.save()
            return redirect('collection_list')
    else:
        form = CollectionForm()
    return render(request, 'main/collection_form.html', {'form': form})

@login_required
@transaction.atomic
def scrape_recipe(request):
    if request.method == 'POST':
        recipe_url = request.POST.get('recipe_url')
        collection_id = request.POST.get('collection_id')
        collection = get_object_or_404(Collection, id=collection_id, user=request.user)
        
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
            return redirect('collection_detail', pk=collection.id)
        
        # Parse the page content
        soup = BeautifulSoup(response.text, 'html.parser')
        raw_text = soup.get_text(separator='\n')  # Use separator to preserve line breaks
        
        # Parse the raw text into structured data using GenAI
        structured_data = parse_recipe_with_genai(raw_text)
        # import pdb; pdb.set_trace()
        if not structured_data:
            logger.error(f"Failed to parse the recipe from URL: {recipe_url}")
            messages.error(request, "Failed to parse the recipe. Please try again.")
            return redirect('collection_detail', pk=collection.id)
        
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
            
            messages.success(request, "Recipe scraped and added successfully!")
            logger.info(f"Successfully scraped and saved recipe from URL: {recipe_url} for Collection ID: {collection.id}")
        except Exception as e:
            logger.exception(f"An error occurred while saving the recipe from URL: {recipe_url}. Error: {e}")
            messages.error(request, f"An error occurred while saving the recipe: {e}")
            return redirect('collection_detail', pk=collection.id)
        
        return redirect('meal_detail', pk=meal.id)
    else:
        return redirect('home')

@login_required
def meal_plan(request):
    collections = Collection.objects.filter(user=request.user)
    return render(request, 'main/meal_plan.html', {'collections': collections})

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
    meal = get_object_or_404(Meal, pk=pk, collection__user=request.user)
    recipes = meal.recipes.all()
    
    context = {
        'meal': meal,
        'recipes': recipes,
    }
    
    return render(request, 'main/meal_detail.html', context)

def meal_plan_detail(request, shareable_link):
    """
    Display a meal plan based on the shareable link. Accessible to both authenticated members and unauthenticated users.
    """
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    
    # Check if user is authenticated and is a member
    if request.user.is_authenticated:
        is_member = Membership.objects.filter(user=request.user, meal_plan=meal_plan).exists()
    else:
        is_member = False

    meal_plan_recipes = meal_plan.meals.values_list('id', flat=True) if meal_plan else []

    context = {
        'meal_plan': meal_plan,
        'is_member': is_member,
        'meal_plan_recipes': meal_plan_recipes
    }
    
    return render(request, 'main/meal_plan_detail.html', context)

@login_required
def join_meal_plan(request, shareable_link):
    """
    Allow a user to join a meal plan using its shareable link.
    """
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    
    # Check if user is already a member
    if Membership.objects.filter(user=request.user, meal_plan=meal_plan).exists():
        messages.error(request, "You are already a member of this meal plan.")
        return redirect('meal_plan_detail', shareable_link=shareable_link)
    
    # Add user to the meal plan
    Membership.objects.create(user=request.user, meal_plan=meal_plan)
    messages.success(request, f"You have successfully joined the meal plan '{meal_plan.name}'.")
    return redirect('meal_plan_detail', shareable_link=shareable_link)

@login_required
def leave_meal_plan(request, shareable_link):
    """
    Allow a user to leave their current meal plan.
    """
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    if request.user == meal_plan.owner:
        messages.error(request, "Owners cannot leave their own meal plan.")
        return redirect('meal_plan_detail', shareable_link=shareable_link)
    
    membership = Membership.objects.filter(user=request.user, meal_plan=meal_plan).first()
    if membership:
        membership.delete()
        messages.success(request, f"You have left the meal plan '{meal_plan.name}'.")
    else:
        messages.error(request, "You are not a member of this meal plan.")
    
    return redirect('collection_list')

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
        return redirect('collection_detail', pk=request.GET.get('collection_id'))

    meal = get_object_or_404(Meal, id=meal_id, collection__user=request.user)
    
    if meal_plan.meals.filter(id=meal.id).exists():
        meal_plan.meals.remove(meal)
        messages.info(request, f"'{meal.title}' has been removed from your meal plan.")
    else:
        meal_plan.meals.add(meal)
        messages.success(request, f"'{meal.title}' has been added to your meal plan.")
    
    meal_plan.save()
    
    next_url = request.POST.get('next')
    return redirect(next_url)

@require_POST
@login_required
def delete_meal(request, meal_id):
    if request.method == 'POST':
        meal = get_object_or_404(Meal, id=meal_id)
        meal.delete()
    
    next_url = request.POST.get('next')
    return redirect(next_url)

@require_POST
@login_required
def create_grocery_list(request, shareable_link):
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    ingredients = gather_ingredients(meal_plan)
    grocery_list_instruction = request.POST.get('grocery_list_instruction', '')
    formatted_list = summarize_grocery_list_with_genai(ingredients, grocery_list_instruction)
    meal_plan.grocery_list = formatted_list
    meal_plan.grocery_list_instruction = grocery_list_instruction
    meal_plan.save()
    return redirect('meal_plan_detail', shareable_link=shareable_link)

@require_POST
@login_required
def save_grocery_list(request, shareable_link):
    meal_plan = get_object_or_404(MealPlan, shareable_link=shareable_link)
    if request.method == 'POST':
        meal_plan.grocery_list = request.POST.get('grocery_list', '')
        meal_plan.save()
    return redirect('meal_plan_detail', shareable_link=meal_plan.shareable_link)
    
def gather_ingredients(meal_plan):
    ingredients = []
    for meal in meal_plan.meals.all():
        for recipe in meal.recipes.all():
            ingredients.extend(recipe.ingredients.all())
    return ingredients