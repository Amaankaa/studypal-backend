from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Notebook, Note, Flashcard, Quiz, Question
from .serializers import NotebookSerializer, NoteSerializer, FlashcardSerializer, QuizSerializer, QuestionSerializer, UserRegistrationSerializer, UserProfileSerializer

import google.generativeai as genai
import json
import random
from django.contrib.auth import get_user_model
User = get_user_model()

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
    except Exception as e:
        print(f"Database error: {e}")
        return Response({"error": "Database error"}, status=500)

    # Allow temperature to be set via request, default to 1.0 for more randomness
    temperature = float(request.data.get('temperature', 1.0))
    variation = request.data.get('variation', None)

    prompt = f"""
    Generate 5 unique multiple choice questions based on the following note:
    \"\"\"{note.content}\"\"\"
    {f'Variation: {variation}' if variation else ''}

    Respond ONLY with a valid JSON list of dictionaries formatted like this:
    [
      {{
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "correct": "B"
      }},
      ...
    ]

    If you have generated questions for this note before, do NOT repeat them. Make these questions as different as possible from previous ones.
    """

    try:
        # Check if API key is configured
        if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
            return Response({"error": "AI service not configured"}, status=500)

        model = genai.GenerativeModel(
            'gemini-2.0-flash',
            generation_config={
                "response_mime_type": "application/json",
                "temperature": temperature
            }
        )
        
        print(f"Calling Gemini API with prompt length: {len(prompt)}")
        response = model.generate_content(prompt)
        content = response.text
        print(f"Received response from Gemini: {content[:200]}...")

        try:
            quiz_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw content: {content}")
            return Response({
                "error": "Could not parse Gemini output",
                "raw": content
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

        return Response({"message": "Quiz generated successfully", "quiz_id": quiz.id}, status=201)

    except Exception as e:
        error_message = str(e)
        print(f"Error in generate_quiz: {error_message}")
        
        # Handle quota exceeded error
        if "429" in error_message or "quota" in error_message.lower() or "exceeded" in error_message.lower():
            return Response({
                "error": "AI service quota exceeded. Please try again tomorrow or upgrade your plan.",
                "details": "You've reached the daily limit for AI requests."
            }, status=429)
        
        # Handle other AI errors
        elif "google.api_core.exceptions" in str(type(e)):
            return Response({
                "error": "AI service temporarily unavailable. Please try again later.",
                "details": error_message
            }, status=503)
        
        # Handle other errors
        else:
            return Response({
                "error": "Failed to generate quiz. Please try again.",
                "details": error_message
            }, status=500)
    try:
        note = Note.objects.get(id=note_id, notebook__user=request.user)
    except Note.DoesNotExist:
        return Response({"error": "Note not found"}, status=404)
    except Exception as e:
        print(f"Database error: {e}")
        return Response({"error": "Database error"}, status=500)

    # Allow temperature to be set via request, default to 1.0 for more randomness
    temperature = float(request.data.get('temperature', 1.0))
    variation = request.data.get('variation', None)

    prompt = f"""
    Generate 5 unique multiple choice questions based on the following note:
    \"\"\"{note.content}\"\"\"
    {f'Variation: {variation}' if variation else ''}

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
        # Check if API key is configured
        if not settings.GEMINI_API_KEY:
            return Response({"error": "AI service not configured"}, status=500)

        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config={
                "response_mime_type": "application/json",
                "temperature": temperature
            }
        )
        
        print(f"Calling Gemini API with prompt length: {len(prompt)}")
        response = model.generate_content(prompt)
        content = response.text
        print(f"Received response from Gemini: {content[:200]}...")

        try:
            quiz_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw content: {content}")
            return Response({
                "error": "Could not parse Gemini output",
                "raw": content
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

        return Response({"message": "Quiz generated successfully", "quiz_id": quiz.id}, status=201)

    except Exception as e:
        print(f"Error in generate_quiz: {e}")
        import traceback
        traceback.print_exc()
        return Response({"error": f"AI generation failed: {str(e)}"}, status=500)
    try:
        note = Note.objects.get(id=note_id, notebook__user=request.user)
    except Note.DoesNotExist:
        return Response({"error": "Note not found"}, status=404)

    # Allow temperature to be set via request, default to 1.0 for more randomness
    temperature = float(request.data.get('temperature', 1.0))
    variation = request.data.get('variation', None)

    prompt = f"""
    Generate 5 unique multiple choice questions based on the following note:
    \"\"\"{note.content}\"\"\"
    {f'Variation: {variation}' if variation else ''}

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
            generation_config={
                "response_mime_type": "application/json",
                "temperature": temperature
            }
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

        return Response({"message": "Quiz generated successfully", "quiz_id": quiz.id}, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quizzes(request, note_id):
    try:
        quizzes = Quiz.objects.filter(note__id=note_id, note__notebook__user=request.user).order_by('-created_at')
        if not quizzes.exists():
            return Response({"error": "No quizzes found for this note"}, status=404)
        quizzes_data = []
        for quiz in quizzes:
            questions = Question.objects.filter(quiz=quiz)
            serialized_questions = [
                {
                    "question": q.question,
                    "options": q.options,
                    "correct": q.correct
                } for q in questions
            ]
            quizzes_data.append({
                "quiz_id": quiz.id,
                "created_at": quiz.created_at,
                "questions": serialized_questions
            })
        return Response({
            "note_id": note_id,
            "quizzes": quizzes_data
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quiz(request, note_id):
    try:
        quizzes = Quiz.objects.filter(note__id=note_id, note__notebook__user=request.user).order_by('-created_at')
        if not quizzes.exists():
            return Response({"error": "Quiz not found"}, status=404)
        
        # Return the latest quiz (or let frontend choose)
        quiz = quizzes.first()
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
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_flashcards(request, note_id):
    try:
        note = Note.objects.get(id=note_id, notebook__user=request.user)
    except Note.DoesNotExist:
        return Response({"error": "Note not found"}, status=404)

    prompt = f"""
    Generate 5 flashcards based on the following note content:
    \"\"\"{note.content}\"\"\"

    Respond ONLY with a valid JSON list of dictionaries formatted like this:
    [
      {{
        "question": "What is...?",
        "answer": "The answer is..."
      }},
      ...
    ]

    If you have generated questions for this note before, do NOT repeat them. Make these questions as different as possible from previous ones.
    """

    try:
        if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
            return Response({"error": "AI service not configured"}, status=500)

        model = genai.GenerativeModel(
            'gemini-2.0-flash',
            generation_config={"response_mime_type": "application/json"}
        )
        print(f"Calling Gemini API for flashcards with prompt length: {len(prompt)}")
        response = model.generate_content(prompt)
        content = response.text
        print(f"Received response from Gemini: {content[:200]}...")

        try:
            flashcard_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw content: {content}")
            return Response({
                "error": "Could not parse Gemini output",
                "raw": content
            }, status=500)

        # Validate structure before saving to DB
        if not isinstance(flashcard_data, list) or not all(
            isinstance(fc, dict) and
            'question' in fc and
            'answer' in fc
            for fc in flashcard_data
        ):
            return Response({"error": "Invalid flashcard format"}, status=400)

        # Create flashcards
        created_flashcards = []
        for fc in flashcard_data:
            flashcard = Flashcard.objects.create(
                note=note,
                question=fc['question'],
                answer=fc['answer']
            )
            created_flashcards.append({
                "id": flashcard.id,
                "question": flashcard.question,
                "answer": flashcard.answer
            })

        return Response({
            "message": f"Generated {len(created_flashcards)} flashcards successfully",
            "flashcards": created_flashcards
        }, status=201)

    except Exception as e:
        error_message = str(e)
        print(f"Error in generate_flashcards: {error_message}")

        if "429" in error_message or "quota" in error_message.lower() or "exceeded" in error_message.lower():
            return Response({
                "error": "AI service quota exceeded. Please try again tomorrow or upgrade your plan.",
                "details": "You've reached the daily limit for AI requests."
            }, status=429)
        elif "google.api_core.exceptions" in str(type(e)):
            return Response({
                "error": "AI service temporarily unavailable. Please try again later.",
                "details": error_message
            }, status=503)
        else:
            return Response({
                "error": "Failed to generate flashcards. Please try again.",
                "details": error_message
            }, status=500)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_flashcards_for_note(request, note_id):
    try:
        note = Note.objects.get(id=note_id, notebook__user=request.user)
    except Note.DoesNotExist:
        return Response({"error": "Note not found"}, status=404)

    flashcards = Flashcard.objects.filter(note=note)
    serialized_flashcards = [
        {
            "id": fc.id,
            "question": fc.question,
            "answer": fc.answer
        } for fc in flashcards
    ]
    return Response({
        "note_id": note.id,
        "note_title": note.title,
        "flashcards": serialized_flashcards
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user
    if request.method == 'GET':
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)