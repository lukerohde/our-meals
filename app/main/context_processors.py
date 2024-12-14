from .models import MealPlan, Membership

def latest_meal_plan(request):
    if request.user.is_authenticated:
        membership = request.user.memberships.order_by('-joined_at').first()
        if membership:
            return {'latest_meal_plan': membership.meal_plan}
    return {} 