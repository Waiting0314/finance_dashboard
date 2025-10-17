from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required
from stocks.views import dashboard

# A simple view to redirect authenticated users to the dashboard
def home_redirect(request):
    if request.user.is_authenticated:
        return RedirectView.as_view(pattern_name='dashboard', permanent=False)(request)
    else:
        # If you have a specific landing page for non-authenticated users
        # you can render it here. For now, we redirect to login.
        return RedirectView.as_view(pattern_name='login', permanent=False)(request)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('users/', include('django.contrib.auth.urls')),
    path('stocks/', include('stocks.urls')),
    path('', home_redirect, name='home'),
]