from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('switch/<int:user_id>/', views.switch_user, name='switch_user'),
    path('u/<str:username>/', views.profile_view, name='profile'),
]
