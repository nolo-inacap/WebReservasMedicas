from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register', views.register_view, name='register'),
    path('home/', views.home, name='home'),
    path('citas/', views.citas_view, name='citas'),
    path('logout/', views.logout_view, name='logout'),
    path('mis-citas/', views.mis_citas, name='mis_citas'),
    path('reserve/<int:id>/', views.reserve_view, name='reserve'),
    path('eliminar-cita/<str:cita_id>/', views.eliminar_cita, name='eliminar_cita'),
    path('editar-cita/<str:cita_id>/', views.editar_cita, name='editar_cita'),
]