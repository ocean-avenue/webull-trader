from django.urls import path, include
from old_ross import views

urlpatterns = [
    path('', views.index, name='dashboard'),
]
