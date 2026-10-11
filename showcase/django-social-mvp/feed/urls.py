from django.urls import path
from . import views

urlpatterns = [
    path('', views.feed_list, name='feed'),
    path('post/<int:post_id>/like/', views.toggle_like, name='toggle_like'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
]
