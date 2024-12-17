from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter

class InviteOnlyAccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        # ensure the user is joining a meal plan i.e. has an invite
        return 'joining_shareable_link' in request.session
        
    def get_signup_redirect_url(self, request):
        joining_link = request.session.get('joining_shareable_link')
        logger.debug(f"get_signup_redirect_url: joining_shareable_link = {joining_link}")
        if joining_link:
            return reverse('meal_plan_detail', kwargs={'shareable_link': joining_link})
        return super().get_signup_redirect_url(request)