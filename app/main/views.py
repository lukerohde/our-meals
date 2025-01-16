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
from .ai_helpers import summarize_grocery_list_with_genai, parse_recipe_with_genai
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
import uuid
from django.core.files.storage import default_storage
import os
from django.conf import settings
import base64
from PIL import Image
import pillow_heif
from io import BytesIO
from django.core.files.base import ContentFile
import re

# Configure logger
logger = logging.getLogger(__name__)

def get_possessive_name(name):
    """Convert a name to its possessive form."""
    if name.endswith('s'):
        return f"{name}'"
    return f"{name}'s"

def get_recipe_text_from_url(url):
    """Get recipe text from a URL"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract main content
        article = soup.find('article') or soup.find('main') or soup.find('body')
        if not article:
            return response.text
            
        # Remove unwanted elements
        for element in article.find_all(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
            
        return article.get_text()
        
    except Exception as e:
        logger.error(f"Error fetching recipe from URL: {str(e)}")
        raise ValueError(f"Failed to access the recipe URL: {str(e)}")

def extract_urls_from_text(text):
    """Extract URLs from text using regex pattern"""
    url_pattern = r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F]{2}))+'
    return re.findall(url_pattern, text)

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
    """Scrape and parse a recipe from text, URLs, or photos"""
    try:

        #collection = get_object_or_404(Collection, id=collection_id, user=request.user)
        collection = get_object_or_404(Collection, id=collection_id, user__in=User.objects.filter(memberships__meal_plan__in=request.user.memberships.values('meal_plan')))
        
        # Get recipe text/URLs and photos
        recipe_text_and_urls = request.POST.get('recipe_text_and_urls', '').strip()
        photo_urls = []
        # Collect photo URLs from request
        i = 0
        while f'photo_{i}' in request.POST:
            photo_url = request.POST[f'photo_{i}'].strip()
            if photo_url:  # Only add non-empty photo URLs
                photo_urls.append(photo_url)
            i += 1
        
        if not recipe_text_and_urls and not photo_urls:
            raise ValueError("Please provide recipe text, URLs, or photos")

        # Extract URLs from text and get their content
        raw_text = recipe_text_and_urls
        if recipe_text_and_urls:
            urls = extract_urls_from_text(recipe_text_and_urls)
            for url in urls:
                url_text = get_recipe_text_from_url(url)
                if url_text:
                    # Create the Markdown heading and recipe text
                    markdown_text = f"\n\n## {url}\n\n{url_text}\n\n"
                    # Replace the URL in the original text with the Markdown text
                    raw_text = raw_text.replace(url, markdown_text)
        
        # Parse recipe with text and/or photos
        recipe_data = parse_recipe_with_genai(raw_text=raw_text if raw_text else None, photos=photo_urls)
        
        # Create meal from recipe data
        try:
            meal = create_meal_from_recipe_data(collection, recipe_data)
        except Exception as e:
            raise ValueError(f"Our AI made a bit of a boo-boo translating the recipe into computer language.  It's worth giving them another chance.")
        
        logger.info(f"Created Meal: {meal.title} (ID: {meal.id})")
        messages.success(request, "Recipe successfully imported!")
        redirect_url = reverse('main:meal_detail', args=[meal.id])

        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'message': 'Recipe successfully imported!',
                'status': 'success',
                'redirect': redirect_url
            })
        # Regular form submission
        return redirect(redirect_url)
        
    except Http404:
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'message': 'Access denied to collection.',
                'status': 'error'
            }, status=403)
        return HttpResponseForbidden()

    except Exception as e:
        logger.error(f"Error scraping recipe: {str(e)}", exc_info=True)
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'message': str(e),
                'status': 'error'
            }, status=400)
        
        messages.error(request, str(e))
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

@login_required
def meal_edit(request, pk):
    meal = get_object_or_404(Meal, pk=pk)
    
    # Check if user has access to this meal through collection
    if meal.collection.user != request.user:
        return HttpResponseForbidden("You don't have permission to edit this meal")
    
    # Convert meal to text format
    meal_text = f"{meal.title}\n\n"
    if meal.description:
        meal_text += f"{meal.description}\n\n"
    
    for recipe in meal.recipes.all():
        meal_text += f"# {recipe.title}\n"
        if recipe.description:
            meal_text += f"{recipe.description}\n\n"
        
        meal_text += "## Ingredients\n"
        for ingredient in recipe.ingredients.all():
            amount_str = f"{ingredient.amount} " if ingredient.amount else ""
            meal_text += f"- {amount_str}{ingredient.unit} {ingredient.name}\n"
        
        meal_text += "\n## Method\n"
        for step in recipe.method_steps.all():
            meal_text += f"- {step.description}\n"
        meal_text += "\n"
    
    if request.method == "POST":
        new_text = request.POST.get('meal_text')
        try:
            # Parse the text back into structured data
            parsed_data = parse_recipe_with_genai(raw_text=new_text)
            
            with transaction.atomic():
                # Update meal
                meal.title = parsed_data['title']
                meal.description = parsed_data.get('description', '')
                meal.save()
                
                # Clear existing recipes
                meal.recipes.all().delete()
                
                # Create new recipes
                for recipe_data in parsed_data['recipes']:
                    recipe = Recipe.objects.create(
                        meal=meal,
                        title=recipe_data['title'],
                        description=recipe_data.get('description', '')
                    )
                    
                    # Create ingredients
                    for ing_data in recipe_data.get('ingredients', []):
                        Ingredient.objects.create(
                            recipe=recipe,
                            name=ing_data['name'],
                            amount=ing_data.get('amount'),
                            unit=ing_data.get('unit', '')
                        )
                    
                    # Create method steps
                    for step_data in recipe_data.get('method', []):
                        MethodStep.objects.create(
                            recipe=recipe,
                            description=step_data
                        )
            
            messages.success(request, "Meal updated successfully!")
            
            if request.accepts('application/json'):
                return JsonResponse({
                    'redirect': reverse('main:meal_detail', args=[meal.pk])
                })
            return redirect('main:meal_detail', pk=meal.pk)
            
        except Exception as e:
            error_message = str(e)
            messages.error(request, f"Error parsing meal text: {error_message}")
            if request.accepts('application/json'):
                return JsonResponse({
                    'message': error_message
                }, status=400)
            return render(request, 'main/meal_edit.html', {'meal': meal, 'meal_text': new_text})
    
    context = {
        'meal': meal,
        'meal_text': meal_text
    }
    
    return render(request, 'main/meal_edit.html', context)

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
    
    # Check if user is a member
    if not meal_plan.memberships.filter(user=request.user).exists():
        raise Http404("Meal plan not found")
    
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

def create_meal_from_recipe_data(collection, recipe_data):
    meal = Meal.objects.create(
        title=recipe_data.get('title', 'New Meal'),
        collection=collection,
        description=recipe_data.get('description', ''),
        url=recipe_data.get('url', '')
    )
    
    for recipe in recipe_data.get('recipes', []):
        recipe_obj = Recipe.objects.create(
            meal=meal,
            title=recipe.get('title', ''),
            description=recipe.get('description', ''),
        )
        
        for ingredient in recipe.get('ingredients', []):
            Ingredient.objects.create(
                recipe=recipe_obj,
                name=ingredient.get('name', ''),
                amount=ingredient.get('amount', None),
                unit=ingredient.get('unit', '')
            )
        
        for step in recipe.get('method', []):
            MethodStep.objects.create(
                recipe=recipe_obj,
                description=step.strip()
            )
    
    return meal

def convert_to_jpeg(image_file):
    """Convert any image to JPEG format"""
    try:
        content_type = getattr(image_file, 'content_type', '')
        
        if content_type == 'image/heic':
            # Handle HEIC format
            heif_file = pillow_heif.read_heif(image_file)
            img = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
                heif_file.mode,
                heif_file.stride,
            )
        else:
            # Handle other formats
            img = Image.open(image_file)
        
        # Convert to RGB if necessary (handles PNG with alpha channel)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as JPEG to BytesIO
        output = BytesIO()
        img.save(output, format='JPEG', quality=95)
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error converting image: {str(e)}")
        raise

def encode_image_file(file):
    """Convert an uploaded file to base64"""
    return base64.b64encode(file.read()).decode('utf-8')

@require_POST
@login_required
def upload_photos(request):
    """Handle photo uploads and return their URLs"""
    if not request.FILES:
        return JsonResponse({'error': 'No files provided'}, status=400)
    
    uploaded_urls = []
    for file in request.FILES.getlist('photos'):
        if not file.content_type.startswith('image/'):
            return JsonResponse({'error': 'Only image files are allowed'}, status=400)
            
        # Convert to JPEG
        jpeg_file = convert_to_jpeg(file)
    
        # In production, store in S3
        file_uuid = str(uuid.uuid4())
        file_name = f"recipe_photos/{file_uuid}.jpg"
        saved_name = default_storage.save(file_name, ContentFile(jpeg_file.read()))
        url = default_storage.url(saved_name)

        uploaded_urls.append(url)
    
    return JsonResponse({'urls': uploaded_urls})
