from django.urls import path
from . import views

urlpatterns = [
    path('function', views.hello_world),
    path('class', views.HelloEthiopia.as_view()),
    path('reservation', views.home),
    path('TAform/', views.taform_view, name='taform'),
]