"""
URL configuration for gameplay app.
"""
from django.urls import path
from . import views

app_name = 'gameplay'

urlpatterns = [
    path('', views.game_list, name='game_list'),
    path('create/', views.create_game, name='create_game'),
    path('<uuid:game_id>/', views.game_view, name='game_view'),
]
