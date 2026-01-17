from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('watchlist/remove/<int:stock_id>/', views.remove_from_watchlist, name='remove_from_watchlist'),
    path('refresh/all/', views.refresh_all_stocks, name='refresh_all_stocks'),
    path('api/stock/<str:ticker>/', views.stock_detail_api, name='stock_detail_api'),
    path('stock/<str:ticker>/', views.stock_detail, name='stock_detail'),
    path('api/price/<str:ticker>/', views.get_latest_price, name='get_latest_price'),
    path('api/check-loading-status/', views.check_loading_status, name='check_loading_status'),
]
