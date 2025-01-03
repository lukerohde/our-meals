import os
from openai import OpenAI
import re
import json
import logging
import requests
from bs4 import BeautifulSoup
import json

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

def parse_recipe_with_genai(raw_text):
    # Placeholder function for integrating with GenAI
    # This should send the raw_text to GenAI and receive structured data
    # Example implementation:
    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY')
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Parse the following meal text into structured JSON. The meal JSON contain a title, a description and an array of recipes.  The description should be drawn from the page and also list key tips from reviewer comments. The meal contains an array of recipes. Even though most meals contain only one recipe, some have multiple recipes such as sauces, salads and sides.  Each recipe has a title, an optional description, an array of ingredients and a method as an array of steps.  Each ingredient has a name, an amount, and a unit. Units are standard like cups, tablespoons, teaspoons, grams, pounds, ounces, but using standard abbreviations. Convert fractional amounts to decimals. Amounts should be quoted. Example format: {\"title\": \"Meal Title\", \"description\": \"Description of the meal\", \"recipes\": [{\"title\": \"Recipe Title\", \"description\": \"Description of the recipe\", \"ingredients\": [{\"name\": \"ingredient1\", \"amount\": \"1\", \"unit\": \"cup\"}, {\"name\": \"ingredient2\", \"amount\": \"2\", \"unit\": \"tbsp\"}], \"method\": [\"Step 1\", \"Step 2\"]}]} " },
            {"role": "user", "content": raw_text}
        ]
    )
    response_text = response.choices[0].message.content
    print(response_text)
    try:
        structured_data = extract_json(response_text)
        return structured_data
    except ValueError as e:
        print(f"Error parsing JSON: {e}")
        return None 

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