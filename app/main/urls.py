from django.urls import path
from . import views

app_name = 'main'  

urlpatterns = [
    # Collections
    path('', views.collection_list, name='collection_list'),  
    path('collections/create/', views.collection_create, name='collection_create'),
    path('collections/<int:pk>/', views.collection_detail, name='collection_detail'),
    path('collections/<int:pk>/edit/', views.collection_edit, name='collection_edit'),
    
    # Meals
    path('collections/<int:collection_id>/meals/create/', views.scrape_recipe, name='scrape'),
    path('upload-photos/', views.upload_photos, name='upload_photos'),
    path('meals/<int:pk>/', views.meal_detail, name='meal_detail'),  
    path('meals/<int:pk>/edit/', views.meal_edit, name='meal_edit'),  
    path('meals/<int:pk>/edit/save/', views.meal_edit_post, name='meal_edit_post'),  
    path('meals/<int:pk>/delete/', views.delete_meal, name='delete_meal'),
    
    # Meal Plans
    path('meal-plans/<uuid:shareable_link>/', views.meal_plan_detail, name='meal_plan_detail'),
    path('meal-plans/<uuid:shareable_link>/join/', views.join_meal_plan, name='join_meal_plan'),
    path('meal-plans/<uuid:shareable_link>/leave/', views.leave_meal_plan, name='leave_meal_plan'),
    path('meal-plans/<uuid:shareable_link>/edit/', views.meal_plan_edit, name='meal_plan_edit'),
    path('meal-plans/<uuid:shareable_link>/members/<int:member_id>/', views.remove_member, name='remove_member'),
    path('meal-plans/<uuid:shareable_link>/meals/<int:meal_id>/', views.toggle_meal_in_meal_plan, name='toggle_meal_in_meal_plan'),
    
    # Grocery Lists
    path('meal-plans/<uuid:shareable_link>/create-grocery-list/', views.create_grocery_list, name='create_grocery_list'),
    path('meal-plans/<uuid:shareable_link>/save-grocery-list/', views.save_grocery_list, name='save_grocery_list'),
]