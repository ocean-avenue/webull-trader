from django.urls import path, include
from old_ross import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('analytics', views.analytics, name='analytics'),
    path('analytics/<str:date>', views.analytics_date, name='analytics_date'),
    path('analytics/<str:date>/<str:symbol>', views.analytics_date_symbol, name='analytics_date_symbol'),
    path('reports/hourly', views.reports_hourly, name='reports_hourly'),
]
