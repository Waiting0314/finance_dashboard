from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('watchlist/remove/<int:stock_id>/', views.remove_from_watchlist, name='remove_from_watchlist'),
    path('stock/<str:ticker>/', views.stock_detail, name='stock_detail'),
]
