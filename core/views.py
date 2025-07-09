from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Notebook, Note, Flashcard, Quiz, Question
from .serializers import NotebookSerializer, NoteSerializer, FlashcardSerializer, QuizSerializer, QuestionSerializer

import google.generativeai as genai
import json

genai.configure(api_key=settings.GEMINI_API_KEY)

class NotebookViewSet(viewsets.ModelViewSet):
    serializer_class = NotebookSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Note.objects.filter(notebook__user=self.request.user)


class FlashcardViewSet(viewsets.ModelViewSet):
    serializer_class = FlashcardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Flashcard.objects.filter(note__notebook__user=self.request.user)

class QuizViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(note__notebook__user=self.request.user)

class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Question.objects.filter(quiz__note__notebook__user=self.request.user)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_quiz(request, note_id):
    try:
        note = Note.objects.get(id=note_id, notebook__user=request.user)
    except Note.DoesNotExist:
        return Response({"error": "Note not found"}, status=404)

    prompt = f"""
    Generate 5 multiple choice questions based on the following note:
    \"\"\"{note.content}\"\"\"

    Respond ONLY with a valid JSON list of dictionaries formatted like this:
    [
      {{
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "correct": "B"
      }},
      ...
    ]
    """

    try:
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config={"response_mime_type": "application/json"}
        )
        response = model.generate_content(prompt)
        content = response.text

        try:
            quiz_data = json.loads(content)
        except json.JSONDecodeError:
            return Response({
                "error": "Could not parse Gemini output",
                "raw": content  # helpful for debugging
            }, status=500)

        # Validate structure before saving to DB
        if not isinstance(quiz_data, list) or not all(
            isinstance(q, dict) and
            'question' in q and
            'options' in q and
            'correct' in q and
            isinstance(q['options'], list)
            for q in quiz_data
        ):
            return Response({"error": "Invalid quiz format"}, status=400)

        quiz = Quiz.objects.create(note=note)
        for q in quiz_data:
            Question.objects.create(
                quiz=quiz,
                question=q['question'],
                options=q['options'],
                correct=q['correct']
            )

        return Response({"message": "Quiz generated successfully"}, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quiz(request, note_id):
    try:
        quiz = Quiz.objects.get(note__id=note_id, note__notebook__user=request.user)
    except Quiz.DoesNotExist:
        return Response({"error": "Quiz not found"}, status=404)

    questions = Question.objects.filter(quiz=quiz)
    serialized_questions = [
        {
            "question": q.question,
            "options": q.options,
            "correct": q.correct
        } for q in questions
    ]
    return Response({
        "quiz_id": quiz.id,
        "questions": serialized_questions
    })