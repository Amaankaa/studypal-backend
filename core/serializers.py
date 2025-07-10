from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notebook, Note, Flashcard, Quiz, Question

class NotebookSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = Notebook
        fields = '__all__'

class NoteSerializer(serializers.ModelSerializer):
    notebook_title = serializers.ReadOnlyField(source='notebook.title')
    
    class Meta:
        model = Note
        fields = '__all__'

class FlashcardSerializer(serializers.ModelSerializer):
    note_title = serializers.ReadOnlyField(source='note.title')
    
    class Meta:
        model = Flashcard
        fields = '__all__'

class QuizSerializer(serializers.ModelSerializer):
    note_title = serializers.ReadOnlyField(source='note.title')
    
    class Meta:
        model = Quiz
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    quiz_id = serializers.ReadOnlyField(source='quiz.id')
    
    class Meta:
        model = Question
        fields = '__all__'

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id', 'username', 'email')