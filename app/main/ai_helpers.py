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
            raise ValueError("No JSON content found in the response.")
    
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
            "content": """
Parse the following recipe content into structured JSON. 
The meal JSON contains a title, a description, and an array of recipes. 
The description should be drawn from the content and also list key tips from reviewer comments if available. 
The meal contains an array of recipes. 
Even though most meals contain only one recipe, some have multiple recipes such as sauces, salads, and sides. 
Each recipe has a title, an optional description, an array of ingredients, and a method as an array of steps. 
Each ingredient has a name, an amount, and a unit. 
Units are standard like cups, tablespoons, teaspoons, grams, pounds, ounces, but using standard abbreviations. 
Convert fractional amounts to decimals. Amounts should be quoted. 
Example format: {"title": "Meal Title", "description": "Description of the meal", "recipes": [{"title": "Recipe Title", "description": "Description of the recipe", "ingredients": [{"name": "ingredient1", "amount": "1", "unit": "cup"}, {"name": "ingredient2", "amount": "2", "unit": "tbsp"}], "method": ["Step 1", "Step 2"]}]}"""
        }
    ]

    # Build the user message content
    content = []
    
    # Add instruction based on what's provided
    if raw_text and photos:
        content.append({
            "type": "text",
            "text": "Please analyze this recipe text and these photos to provide structured recipe information:\n\n" + raw_text
        })
    elif raw_text:
        content.append({
            "type": "text",
            "text": raw_text
        })
    else:  # photos only
        content.append({
            "type": "text",
            "text": "Please analyze these recipe photos to provide structured recipe information:"
        })
    
    # Add photos if provided
    if photos:
        for photo in photos:
            # In development or if URL is local, convert to base64
            if settings.DEBUG or (isinstance(photo, str) and photo.startswith('/')):
                photo_url = get_image_as_base64(photo)
            else:
                photo_url = photo

            content.append({
                "type": "image_url",
                "image_url": {
                    "url": photo_url
                }
            })
    
    messages.append({
        "role": "user",
        "content": content
    })
    
    # Call GPT-4 with appropriate parameters
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=4096,
        temperature=0.7,  # Balance between creativity and consistency
        presence_penalty=0.0,  # No need to encourage topic changes
        frequency_penalty=0.0  # No need to discourage repetition
    )

    # Extract and parse the JSON response
    result = extract_json(response.choices[0].message.content)
    if not result:
        raise ValueError("Failed to parse recipe information")
        
    return result

def parse_recipe_with_photos(photos, existing_data=None):
    """
    Parse recipe information from photos using GPT-4 Vision.
    If existing_data is provided, it will be used as context for the analysis.
    """
    # This function is now deprecated - functionality merged into parse_recipe_with_genai
    raise NotImplementedError("This function is deprecated. Use parse_recipe_with_genai instead.")

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


def scrape_recipe_from_url(recipe_url):
    """
    Scrapes a recipe from the given URL and returns structured data.
    """
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
                        'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                        'Chrome/58.0.3029.110 Safari/537.3',
        'Referer': 'https://www.google.com/',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive'
    }
    
    try:
        response = requests.get(recipe_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        recipe_text = extract_recipe_text(soup)
        result = parse_recipe_with_genai(recipe_text)
        return result
        
    except Exception as e:
        logger.error(f"Error scraping recipe from {recipe_url}: {str(e)}")
        raise ValueError(f"Failed to scrape recipe: {str(e)}")


def extract_recipe_text(soup):
    """Extract recipe text from HTML"""
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text and normalize whitespace
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    text = ' '.join(line for line in lines if line)
    return text