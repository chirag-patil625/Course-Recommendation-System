from django.db import models
from django.utils import timezone

class UserInterest(models.Model):
    user_id = models.CharField(max_length=255)
    interest = models.CharField(max_length=255)

    def __str__(self):
        return f"User {self.user_id}: {self.interest}"
    
class Question(models.Model):
    course = models.CharField(max_length=255, blank=True, null=True)
    text = models.TextField()
    time = models.DateTimeField(default=timezone.now)

def __str__(self):
    return self.text

class UserResponse(models.Model):
    user_id = models.CharField(max_length=255)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True)
    answer = models.TextField()

    def __str__(self):
        return f"User {self.user_id}: {self.answer}"

