from PIL import Image, ImageDraw, ImageFont
import os
import sys

# Add parent directory to path so we can import test fixtures
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_recipe_fixtures import get_mock_recipe_text

# Create a new image with a white background
img = Image.new('RGB', (400, 600), color='white')

# Get a drawing context
draw = ImageDraw.Draw(img)

# Get recipe text from fixtures
recipe_text = get_mock_recipe_text()

# Add text line by line
y_position = 20
for line in recipe_text.split('\n'):
    draw.text((20, y_position), line.strip(), fill='black')
    y_position += 25

# Save the image
img.save('test_recipe_image.jpg')
