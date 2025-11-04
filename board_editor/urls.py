"""
URL configuration for board_editor app.
"""
from django.urls import path
from . import views

app_name = 'board_editor'

urlpatterns = [
    path('', views.editor, name='editor'),
    path('validate-fen/', views.validate_fen, name='validate_fen'),
    path('generate-game-link/', views.generate_game_link, name='generate_game_link'),
    path('save-position/', views.save_position_to_lesson, name='save_position'),
    path('topics-list/', views.get_topics_list, name='topics_list'),
]
