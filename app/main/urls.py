from django.urls import path
from . import views

urlpatterns = [
    path('', views.collection_list, name='collection_list'),
    path('collections/', views.collection_list, name='collection_list'),
    path('collections/create/', views.collection_create, name='collection_create'),
    path('collections/<int:pk>/', views.collection_detail, name='collection_detail'),
    path('meals/<int:pk>/', views.meal_detail, name='meal_detail'),  # New URL pattern
    path('scrape/', views.scrape_recipe, name='scrape'),
    #path('meal-plan/', views.meal_plan, name='meal_plan'),
    path('generate-grocery-list/', views.generate_grocery_list, name='generate_grocery_list'),
    path('meal-plan/<str:shareable_link>/', views.meal_plan_detail, name='meal_plan_detail'),
    path('meal-plan/<str:shareable_link>/join/', views.join_meal_plan, name='join_meal_plan'),
    path('meal-plan/<str:shareable_link>/leave/', views.leave_meal_plan, name='leave_meal_plan'),
    path('toggle-meal/<int:meal_id>/', views.toggle_meal_in_meal_plan, name='toggle_meal_in_meal_plan'),
    path('delete-meal/<int:meal_id>/', views.delete_meal, name='delete_meal'),
    path('meal-plan/<str:shareable_link>/create-grocery-list/', views.create_grocery_list, name='create_grocery_list'),
    path('meal-plan/<str:shareable_link>/save-grocery-list/', views.save_grocery_list, name='save_grocery_list'),
    # Add other URL patterns as needed
] 