def convert_to_grams(amount, unit, region='US'):
    conversion_factors = {
        'US': {
            'cup': 240,  # grams per cup
            'tablespoon': 15,
        },
        'AU': {
            'cup': 250,
            'tablespoon': 20,
        }
    }
    factors = conversion_factors.get(region, {})
    factor = factors.get(unit.lower())
    if factor:
        return amount * factor
    return amount  # Return original amount if unit not found 