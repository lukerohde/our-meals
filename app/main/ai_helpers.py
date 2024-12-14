import os
from openai import OpenAI
import re
import json
import logging

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