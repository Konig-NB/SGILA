from django.urls import path

from schools import views

urlpatterns = [
    path('api/schools/search/', views.school_search, name='school-search'),
]