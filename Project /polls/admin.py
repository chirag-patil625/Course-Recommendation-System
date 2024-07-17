from django.contrib import admin
from .models import Question, UserResponse, UserInterest
admin.site.register(Question)
admin.site.register(UserResponse)
admin.site.register(UserInterest)