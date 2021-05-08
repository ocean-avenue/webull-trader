from django.urls import path, include
from old_ross import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('analytics', views.analytics, name='analytics'),
    path('analytics/<str:date>', views.analytics_detail, name='analytics_detail'),
]
