from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Extend as needed later (profile pic, bio, etc.)
    pass

class Notebook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Note(models.Model):
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Flashcard(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()

class Quiz(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.TextField()
    options = models.JSONField()  # Requires PostgreSQL
    correct = models.CharField(max_length=255)
