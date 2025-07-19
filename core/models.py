from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

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

class StudyGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    public = models.BooleanField(default=True)  # New field for group visibility

    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role})"

class SharedNote(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE)
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('note', 'group')

    def __str__(self):
        return f"{self.note.title} shared in {self.group.name}"

class SharedQuiz(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE)
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('quiz', 'group')

    def __str__(self):
        return f"Quiz {self.quiz.id} shared in {self.group.name}"

class SharedFlashcard(models.Model):
    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE)
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE)
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('flashcard', 'group')

    def __str__(self):
        return f"Flashcard {self.flashcard.id} shared in {self.group.name}"

class SharedLink(models.Model):
    ACCESS_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('group', 'Group Only'),
    ]
    
    # Generate unique ID for URL
    link_id = models.UUIDField(default=uuid.uuid4, unique=True)
    
    # Content type and ID
    content_type = models.CharField(max_length=20)  # 'note', 'quiz', 'flashcard'
    content_id = models.IntegerField()
    
    # Access control
    access_level = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='public')
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, blank=True)  # Optional custom title
    description = models.TextField(blank=True)  # Optional description
    
    def __str__(self):
        return f"{self.content_type} {self.content_id} - {self.access_level}"
    
    @property
    def url(self):
        return f"/shared/{self.link_id}/"

class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('resource', 'Resource'),
        ('system', 'System'),
    ]
    
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # For resource messages
    resource_type = models.CharField(max_length=20, blank=True, null=True)  # 'note', 'quiz', 'flashcard'
    resource_id = models.IntegerField(null=True, blank=True)
    resource_title = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"

class GroupResource(models.Model):
    RESOURCE_TYPES = [
        ('note', 'Note'),
        ('quiz', 'Quiz'),
        ('flashcard', 'Flashcard'),
    ]
    
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='shared_resources')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE)
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES)
    resource_id = models.IntegerField()
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('group', 'resource_type', 'resource_id')
    
    def __str__(self):
        return f"{self.resource_type} {self.resource_id} in {self.group.name}"
    
    @property
    def likes_count(self):
        return self.likes.count()
    
    def is_liked_by(self, user):
        return self.likes.filter(user=user).exists()

class ResourceLike(models.Model):
    resource = models.ForeignKey(GroupResource, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('resource', 'user')
    
    def __str__(self):
        return f"{self.user.username} likes {self.resource}"

class GroupInvitation(models.Model):
    id = models.AutoField(primary_key=True)
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE)
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=16,
        choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')],
        default='pending'
    )

    class Meta:
        unique_together = ('group', 'invited_user', 'status')

# --- Analytics & Progress Tracking Models ---

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.FloatField()
    answers = models.JSONField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} attempted Quiz {self.quiz.id} at {self.attempted_at}" 

class FlashcardAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE)
    correct = models.BooleanField(null=True, blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} reviewed Flashcard {self.flashcard.id} at {self.reviewed_at}"

class UserStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='stats')
    total_points = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Stats for {self.user.username}"

class ActivityLog(models.Model):
    ACTIVITY_TYPES = [
        ('quiz', 'Quiz'),
        ('flashcard', 'Flashcard'),
        ('note', 'Note'),
        ('login', 'Login'),
        ('other', 'Other'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    object_id = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} {self.activity_type} at {self.timestamp}"
