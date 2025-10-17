from django.urls import path
from . import views

urlpatterns = [
    path('function', views.hello_world),
    path('class', views.HelloEthiopia.as_view()),
    path('reservation', views.home),
    path('statistics', views.statistics_view, name='statistics'),
]