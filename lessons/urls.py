"""
URL configuration for lessons app.
"""
from django.urls import path
from . import views
from . import management_views

app_name = 'lessons'

urlpatterns = [
    path('', views.lesson_list, name='lesson_list'),
    path('<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('topic/<int:topic_id>/', views.topic_detail, name='topic_detail'),
    path('position/<int:position_id>/', views.position_viewer, name='position_viewer'),
    path('position/<int:position_id>/complete/', views.mark_position_complete, name='mark_complete'),
    path('position/<int:position_id>/practice/', views.practice_from_position, name='practice_position'),
    path('progress/', views.user_progress_view, name='user_progress'),

    # Teacher Management URLs - Lessons
    path('lesson/create/', management_views.lesson_create, name='lesson_create'),
    path('lesson/<int:pk>/edit/', management_views.lesson_update, name='lesson_update'),
    path('lesson/<int:pk>/delete/', management_views.lesson_delete, name='lesson_delete'),
    path('lesson/<int:pk>/toggle/', management_views.lesson_toggle, name='lesson_toggle'),
    path('lesson/reorder/', management_views.reorder_lessons, name='reorder_lessons'),

    # Teacher Management URLs - Topics
    path('lesson/<int:lesson_pk>/topic/create/', management_views.topic_create, name='topic_create'),
    path('topic/<int:pk>/edit/', management_views.topic_update, name='topic_update'),
    path('topic/<int:pk>/delete/', management_views.topic_delete, name='topic_delete'),
    path('topic/<int:pk>/toggle/', management_views.topic_toggle, name='topic_toggle'),
    path('lesson/<int:lesson_pk>/topic/reorder/', management_views.reorder_topics, name='reorder_topics'),

    # Teacher Management URLs - Positions
    path('topic/<int:topic_pk>/position/create/', management_views.position_create, name='position_create'),
    path('position/<int:pk>/edit/', management_views.position_update, name='position_update'),
    path('position/<int:pk>/delete/', management_views.position_delete, name='position_delete'),
    path('position/<int:pk>/toggle/', management_views.position_toggle, name='position_toggle'),
    path('topic/<int:topic_pk>/position/reorder/', management_views.reorder_positions, name='reorder_positions'),
]
