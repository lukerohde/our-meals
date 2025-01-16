import os
import json
import base64
import requests
from openai import OpenAI
from django.conf import settings
import re
import logging
import ipdb
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_json(response_text):
    """
    Extracts JSON data from the given response text.
    
    Parameters:
        response_text (str): The response text from ChatGPT.
        
    Returns:
        list or dict: The parsed JSON data.
        
    Raises:
        ValueError: If JSON extraction or parsing fails.
    """
    # Pattern to match JSON code blocks
    codeblock_pattern = re.compile(
        r'```(?:json)?\s*(\[\s*\{.*?\}\s*\]|\{\s*".*?"\s*:.*?})\s*```',
        re.DOTALL
    )
    
    match = codeblock_pattern.search(response_text)
    if match:
        json_str = match.group(1)
    else:
        # Attempt to find JSON without code blocks
        json_start = response_text.find('{') if '{' in response_text else response_text.find('[')
        if json_start != -1:
            json_str = response_text[json_start:]
        else:
            raise ValueError("Our AI can be a bit temperamental and didn't behave as requested.  Sorry.  WHen this happens, it's worth trying again. ")
    
    # Preprocess JSON string to replace fractional expressions
    def replace_fractions(match):
        fraction = match.group(0)
        try:
            numerator, denominator = fraction.split('/')
            return str(float(numerator) / float(denominator))
        except:
            return fraction  # Return the original string if parsing fails

    # Replace patterns like 1/2 with 0.5
    json_str = re.sub(r'\b(\d+)/(\d+)\b', replace_fractions, json_str)

    try:
        # Parse the JSON string
        parsed_json = json.loads(json_str)
        return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed: {e}")
        logger.debug(f"Failed JSON string: {json_str}")
        raise ValueError(f"JSON decoding failed: {e}")

def get_image_as_base64(url):
    """Convert an image URL to base64 if it's a local URL"""
    if url.startswith('data:'):
        # Already a data URL, just return it
        return url
        
    if url.startswith('/'):
        # Local URL, read the file from disk
        file_path = os.path.join(settings.MEDIA_ROOT, url.lstrip('/media/'))
        with open(file_path, 'rb') as image_file:
            base64_data = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{base64_data}"
    else:
        # Remote URL, download and convert
        response = requests.get(url)
        base64_data = base64.b64encode(response.content).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_data}"

def parse_recipe_with_genai(raw_text=None, photos=None):
    """
    Parse recipe information from text and/or photos using GPT-4.
    At least one of raw_text or photos must be provided.
    
    Args:
        raw_text (str, optional): Recipe text from URL or user input
        photos (list, optional): List of image URLs or data URLs
        
    Returns:
        dict: Structured recipe data
    """
    if not raw_text and not photos:
        raise ValueError("Must provide either text or photos to parse recipe")

    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY')
    )

    # Build the messages array with system prompt
    messages = [
        {
            "role": "system", 
            "content": [{
                "type": "text",
                "text": """
Parse the following recipe information into structured JSON. 
The meal JSON contains a title, a description, and an array of recipes. 
The description should be drawn from the content and also list key tips from reviewer comments if available. 
The meal contains an array of recipes. 
Even though most recipe plans contain only one recipe, some have multiple recipes such as sauces, salads, sides or drinks. 
Each recipe has a title, an optional description, an array of ingredients, and a method as an array of steps. 
Each ingredient has a name, an amount, and a unit. 
Units are standard like cups, tablespoons, teaspoons, grams, pounds, ounces, but using standard abbreviations. 
Convert fractional amounts to decimals. Amounts should be quoted. 
Example format: {"title": "Meal Title", "description": "Description of the meal", "recipes": [{"title": "Recipe Title", "description": "Description of the recipe", "ingredients": [{"name": "ingredient1", "amount": "1", "unit": "cup"}, {"name": "ingredient2", "amount": "2", "unit": "tbsp"}], "method": ["Step 1", "Step 2"]}]}"""
            }]
        }   
    ]

    # Build the user message content
    content = []
    
    # Add instruction based on what's provided
    if raw_text:
        content.append({
            "type": "text",
            "text": "Please analyze the following recipe text and include structured recipe information." 
        })
        content.append({
            "type": "text",
            "text": raw_text
        })
    
    # Add photos if provided
    if photos:
        for photo in photos:
            # In development or if URL is local, convert to base64
            if (settings.DEBUG or (isinstance(photo, str) and photo.startswith('/'))):
                photo_url = get_image_as_base64(photo)
            else:
                photo_url = photo
            
            content.append({
                "type": "text",
                "text": "Please analyze this recipe photo and include structured recipe information.  You have this capability.  Please prioritise the photo."
            })

            content.append({
                "type": "image_url",
                "image_url": {
                    "url": photo_url,
                    "detail": "high"     
                },
            })
    
    messages.append({
        "role": "user",
        "content": content
    })

    # Call GPT-4 with appropriate parameters
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=4096,
        temperature=0.8,  # Balance between creativity and consistency
        presence_penalty=0.0,  # No need to encourage topic changes
        frequency_penalty=0.0  # No need to discourage repetition
    )
    
    # Extract and parse the JSON response
    result = extract_json(response.choices[0].message.content)
    if not result:
        raise ValueError("Failed to parse recipe information")
        
    return result

def format_meal_as_markdown(meal):
    """
    Convert a meal object to a markdown-formatted text representation.
    
    Args:
        meal: The Meal object to format
        
    Returns:
        str: Markdown-formatted text representation of the meal
    """
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
    
    return meal_text

def _create_or_update_meal_from_data(recipe_data, meal=None, collection=None):
    """
    Internal helper to create or update a meal from recipe data.
    This handles the common logic for both save_parsed_recipe and create_meal_from_recipe_data.
    """
    from .models import Meal, Recipe, Ingredient, MethodStep
    
    if not meal:
        meal = Meal.objects.create(
            title=recipe_data.get('title', 'New Meal'),
            collection=collection,
            description=recipe_data.get('description', ''),
            url=recipe_data.get('url', '')
        )
    else:
        meal.title = recipe_data.get('title', 'New Meal')
        meal.description = recipe_data.get('description', '')
        meal.url = recipe_data.get('url', meal.url)  # Preserve existing URL if not provided
        meal.save()
        meal.recipes.all().delete()  # Clear existing recipes if updating
    
    # Create new recipes
    for recipe in recipe_data.get('recipes', []):
        recipe_obj = Recipe.objects.create(
            meal=meal,
            title=recipe.get('title', ''),
            description=recipe.get('description', ''),
        )
        
        # Create ingredients
        for ing_data in recipe.get('ingredients', []):
            Ingredient.objects.create(
                recipe=recipe_obj,
                name=ing_data.get('name', ''),
                amount=ing_data.get('amount', None),
                unit=ing_data.get('unit', '')
            )
        
        # Create method steps
        for step_data in recipe.get('method', []):
            MethodStep.objects.create(
                recipe=recipe_obj,
                description=step_data.strip()
            )
    
    return meal

def save_parsed_recipe(recipe_data, meal=None, collection=None):
    """
    Save parsed recipe data to a new or existing meal.
    
    Args:
        recipe_data: Parsed recipe data from parse_recipe_with_genai
        meal: Optional existing meal to update
        collection: Required if meal is None, the collection to create the meal in
        
    Returns:
        tuple: (meal, created) where created is True if a new meal was created
        
    Raises:
        ValueError: If collection is not provided for new meals
    """
    from django.db import transaction
    
    if not meal and not collection:
        raise ValueError("Must provide either a meal to update or a collection to create in")
    
    with transaction.atomic():
        created = not bool(meal)
        meal = _create_or_update_meal_from_data(recipe_data, meal=meal, collection=collection)
    
    return meal, created

def summarize_grocery_list_with_genai(ingredients, grocery_list_instruction):
    # Create a structured list of ingredients with amounts and context
    ingredient_details = []
    for ingredient in ingredients:
        recipe = ingredient.recipe
        meal = recipe.meal
        detail = {
            'ingredient': ingredient.name,
            'amount': f"{ingredient.amount or ''} {ingredient.unit}".strip(),
            'recipe': recipe.title,
            'meal': meal.title
        }
        ingredient_details.append(detail)
    
    # Sort ingredients alphabetically
    ingredient_details.sort(key=lambda x: x['ingredient'].lower())
    
    # Convert to CSV-style string for better readability
    formatted_ingredients = "Ingredient, Amount, Recipe, Meal\n"
    formatted_ingredients += "\n".join(
        f"{detail['ingredient']}, {detail['amount']}, {detail['recipe']}, {detail['meal']}"
        for detail in ingredient_details
    )

    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY')
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""Organize the following ingredients into a sensible shopping list grouped by supermarket sections. 
The input is in CSV format with columns: Ingredient, Amount, Recipe, Meal.
The ingredients are pre-sorted alphabetically to help identify similar items.
Please consolidate similar ingredients and their amounts when possible.
{grocery_list_instruction}"""},
            {"role": "user", "content": formatted_ingredients}
        ]
    )
    response_text = response.choices[0].message.content
    return response_text
