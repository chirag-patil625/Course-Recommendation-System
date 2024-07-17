from django.urls import path

from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('chat/', views.index, name='index'),
    path('dynamic-questionnaire/<uuid:user_id>/', views.dynamic_questionnaire, name='questionnaire'),
    path('recommendation/<uuid:user_id>/', views.get_course_recommendation, name='recommendation'),
]  