def get_mock_recipe_text():
    return """
        Classic Chocolate Chip Cookies
        
        These cookies are crispy on the outside, chewy on the inside.
        
        Ingredients:
        - 2 1/4 cups all-purpose flour
        - 1 tsp baking soda
        - 1 cup butter, softened
        - 2 cups chocolate chips
        
        Instructions:
        1. Preheat oven to 375°F
        2. Mix dry ingredients
        3. Cream butter and sugars
        4. Combine and bake
        """

def get_mock_parsed_recipe():
    return {
        "title": "Classic Chocolate Chip Cookies",
        "description": "These cookies are crispy on the outside, chewy on the inside.",
        "recipes": [{
            "title": "Classic Chocolate Chip Cookies",
            "description": "These cookies are crispy on the outside, chewy on the inside.",
            "ingredients": [
                {"name": "all-purpose flour", "amount": "2 1/4", "unit": "cups"},
                {"name": "baking soda", "amount": "1", "unit": "tsp"},
                {"name": "butter", "amount": "1", "unit": "cup", "notes": "softened"},
                {"name": "chocolate chips", "amount": "2", "unit": "cups"}
            ],
            "method": [
                "Preheat oven to 375°F",
                "Mix dry ingredients",
                "Cream butter and sugars",
                "Combine and bake"
            ]
        }]
    }

def get_mock_delayed_response(*args):
    import time
    time.sleep(0.1)  # Small delay to ensure we can see loading state
    return get_mock_recipe_text()
