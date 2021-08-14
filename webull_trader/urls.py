from django.urls import path, include
from webull_trader import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('trading-logs', views.trading_logs, name='trading_logs'),
    path('trading-logs/<str:date>/<int:hour>', views.trading_logs_date_hour, name='trading_logs_date_hour'),
    path('day-analytics', views.day_analytics, name='day_analytics'),
    path('day-analytics/<str:date>', views.day_analytics_date, name='day_analytics_date'),
    path('day-analytics/<str:date>/<str:symbol>', views.day_analytics_date_symbol, name='day_analytics_date_symbol'),
    path('day-reports/price', views.day_reports_price, name='day_reports_price'),
    path('day-reports/mktcap', views.day_reports_mktcap, name='day_reports_mktcap'),
    path('day-reports/float', views.day_reports_float, name='day_reports_float'),
    path('day-reports/turnover', views.day_reports_turnover, name='day_reports_turnover'),
    path('day-reports/short', views.day_reports_short, name='day_reports_short'),
    path('day-reports/gap', views.day_reports_gap, name='day_reports_gap'),
    path('day-reports/relvol', views.day_reports_relvol, name='day_reports_relvol'),
    path('day-reports/sector', views.day_reports_sector, name='day_reports_sector'),
    path('day-reports/holding', views.day_reports_holding, name='day_reports_holding'),
    path('day-reports/plpct', views.day_reports_plpct, name='day_reports_plpct'),
    path('day-reports/hourly', views.day_reports_hourly, name='day_reports_hourly'),
    path('day-reports/daily', views.day_reports_daily, name='day_reports_daily'),
    path('day-reports/weekly', views.day_reports_weekly, name='day_reports_weekly'),
    path('swing-positions', views.swing_positions, name='swing_positions'),
    path('swing-positions/<str:symbol>', views.swing_positions_symbol, name='swing_positions_symbol'),
    path('swing-analytics', views.swing_analytics, name='swing_analytics'),
    path('swing-analytics/<str:symbol>', views.swing_analytics_symbol, name='swing_analytics_symbol'),
]
