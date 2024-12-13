from django.urls import path
from . import views

urlpatterns = [
    path('', views.collection_list, name='collection_list'),
    path('collections/', views.collection_list, name='collection_list'),
    path('collections/create/', views.collection_create, name='collection_create'),
    path('collections/<int:pk>/', views.collection_detail, name='collection_detail'),
    path('meals/<int:pk>/', views.meal_detail, name='meal_detail'),  # New URL pattern
    path('scrape/', views.scrape_recipe, name='scrape'),
    path('meal-plan/', views.meal_plan, name='meal_plan'),
    path('generate-grocery-list/', views.generate_grocery_list, name='generate_grocery_list'),
    # Add other URL patterns as needed
] 