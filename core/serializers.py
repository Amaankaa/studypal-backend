from rest_framework import serializers
from .models import Notebook, Note, Flashcard, Quiz, Question

class NotebookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notebook
        fields = '__all__'

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = '__all__'

class FlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = '__all__'

class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'