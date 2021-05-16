from django.urls import path, include
from webull_trader import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('analytics', views.analytics, name='analytics'),
    path('analytics/<str:date>', views.analytics_date, name='analytics_date'),
    path('analytics/<str:date>/<str:symbol>',
         views.analytics_date_symbol, name='analytics_date_symbol'),
    path('reports/price', views.reports_price, name='reports_price'),
    path('reports/mktcap', views.reports_mktcap, name='reports_mktcap'),
    path('reports/float', views.reports_float, name='reports_float'),
    path('reports/turnover', views.reports_turnover, name='reports_turnover'),
    path('reports/short', views.reports_short, name='reports_short'),
    path('reports/hourly', views.reports_hourly, name='reports_hourly'),
]
