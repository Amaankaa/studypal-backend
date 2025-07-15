from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Notebook, Note, Flashcard, Quiz, Question, StudyGroup, GroupMembership, SharedNote, SharedQuiz, SharedFlashcard, SharedLink, ChatMessage, GroupResource, ResourceLike, GroupInvitation
from .serializers import NotebookSerializer, NoteSerializer, FlashcardSerializer, QuizSerializer, QuestionSerializer, UserRegistrationSerializer, UserProfileSerializer, StudyGroupSerializer, GroupMembershipSerializer, SharedNoteSerializer, SharedQuizSerializer, SharedFlashcardSerializer, SharedLinkSerializer, ChatMessageSerializer, GroupResourceSerializer, GroupInvitationSerializer

import google.generativeai as genai
import json
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
            'gemini-2.5-flash',
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_study_group(request):
    serializer = StudyGroupSerializer(data=request.data)
    if serializer.is_valid():
        group = serializer.save(created_by=request.user)
        # Add creator as admin member
        GroupMembership.objects.create(user=request.user, group=group, role='admin')
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_groups(request):
    memberships = GroupMembership.objects.filter(user=request.user)
    groups = [membership.group for membership in memberships]
    serializer = StudyGroupSerializer(groups, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_groups(request):
    query = request.GET.get('search', '')
    groups = StudyGroup.objects.filter(public=True, name__icontains=query) if query else StudyGroup.objects.filter(public=True)
    serializer = StudyGroupSerializer(groups, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_group(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    # Prevent duplicate membership
    if GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "Already a member"}, status=400)
    GroupMembership.objects.create(user=request.user, group=group, role='member')
    return Response({"message": "Joined group successfully"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_group(request, group_id):
    try:
        membership = GroupMembership.objects.get(user=request.user, group_id=group_id)
    except GroupMembership.DoesNotExist:
        return Response({"error": "Not a member of this group"}, status=404)
    # Prevent admin from leaving if they're the only admin
    if membership.role == 'admin':
        admin_count = GroupMembership.objects.filter(group_id=group_id, role='admin').count()
        if admin_count <= 1:
            return Response({"error": "Cannot leave as the only admin. Assign another admin first."}, status=400)
    membership.delete()
    return Response({"message": "Left group successfully"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_to_group(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    # Only group members can invite
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    username = request.data.get('username')
    if not username:
        return Response({"error": "Username is required"}, status=400)
    try:
        invited_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)
    # Prevent inviting self
    if invited_user == request.user:
        return Response({"error": "You cannot invite yourself"}, status=400)
    # Prevent duplicate pending invitations
    if GroupInvitation.objects.filter(group=group, invited_user=invited_user, status='pending').exists():
        return Response({"error": "User already has a pending invitation"}, status=400)
    # Prevent inviting existing members
    if GroupMembership.objects.filter(user=invited_user, group=group).exists():
        return Response({"error": "User is already a member of the group"}, status=400)
    GroupInvitation.objects.create(
        group=group,
        invited_user=invited_user,
        invited_by=request.user
    )
    return Response({"message": "Invitation sent"}, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_group_members(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    memberships = GroupMembership.objects.filter(group=group)
    serializer = GroupMembershipSerializer(memberships, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_group_details(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    
    # Check if user is a member (for private groups) or if group is public
    is_member = GroupMembership.objects.filter(user=request.user, group=group).exists()
    if not group.public and not is_member:
        return Response({"error": "Access denied"}, status=403)
    
    serializer = StudyGroupSerializer(group)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_note_with_group(request, note_id, group_id):
    try:
        note = Note.objects.get(id=note_id, notebook__user=request.user)
        group = StudyGroup.objects.get(id=group_id)
    except (Note.DoesNotExist, StudyGroup.DoesNotExist):
        return Response({"error": "Note or group not found"}, status=404)
    
    # Check if user is a member of the group
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    
    # Check if already shared
    if SharedNote.objects.filter(note=note, group=group).exists():
        return Response({"error": "Note already shared with this group"}, status=400)
    
    shared_note = SharedNote.objects.create(note=note, group=group, shared_by=request.user)
    serializer = SharedNoteSerializer(shared_note)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_quiz_with_group(request, quiz_id, group_id):
    try:
        quiz = Quiz.objects.get(id=quiz_id, note__notebook__user=request.user)
        group = StudyGroup.objects.get(id=group_id)
    except (Quiz.DoesNotExist, StudyGroup.DoesNotExist):
        return Response({"error": "Quiz or group not found"}, status=404)
    
    # Check if user is a member of the group
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    
    # Check if already shared
    if SharedQuiz.objects.filter(quiz=quiz, group=group).exists():
        return Response({"error": "Quiz already shared with this group"}, status=400)
    
    shared_quiz = SharedQuiz.objects.create(quiz=quiz, group=group, shared_by=request.user)
    serializer = SharedQuizSerializer(shared_quiz)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_flashcard_with_group(request, flashcard_id, group_id):
    try:
        flashcard = Flashcard.objects.get(id=flashcard_id, note__notebook__user=request.user)
        group = StudyGroup.objects.get(id=group_id)
    except (Flashcard.DoesNotExist, StudyGroup.DoesNotExist):
        return Response({"error": "Flashcard or group not found"}, status=404)
    
    # Check if user is a member of the group
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    
    # Check if already shared
    if SharedFlashcard.objects.filter(flashcard=flashcard, group=group).exists():
        return Response({"error": "Flashcard already shared with this group"}, status=400)
    
    shared_flashcard = SharedFlashcard.objects.create(flashcard=flashcard, group=group, shared_by=request.user)
    serializer = SharedFlashcardSerializer(shared_flashcard)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_group_shared_content(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    
    # Check if user is a member of the group
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    
    # Get all shared content
    shared_notes = SharedNote.objects.filter(group=group)
    shared_quizzes = SharedQuiz.objects.filter(group=group)
    shared_flashcards = SharedFlashcard.objects.filter(group=group)
    
    return Response({
        "group_id": group_id,
        "group_name": group.name,
        "shared_notes": SharedNoteSerializer(shared_notes, many=True).data,
        "shared_quizzes": SharedQuizSerializer(shared_quizzes, many=True).data,
        "shared_flashcards": SharedFlashcardSerializer(shared_flashcards, many=True).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_shared_link(request):
    content_type = request.data.get('content_type')
    content_id = request.data.get('content_id')
    access_level = request.data.get('access_level', 'public')
    group_id = request.data.get('group_id')
    title = request.data.get('title', '')
    description = request.data.get('description', '')
    
    # Validate content type
    if content_type not in ['note', 'quiz', 'flashcard']:
        return Response({"error": "Invalid content type"}, status=400)
    
    # Check if content exists and user owns it
    try:
        if content_type == 'note':
            content = Note.objects.get(id=content_id, notebook__user=request.user)
        elif content_type == 'quiz':
            content = Quiz.objects.get(id=content_id, note__notebook__user=request.user)
        elif content_type == 'flashcard':
            content = Flashcard.objects.get(id=content_id, note__notebook__user=request.user)
    except (Note.DoesNotExist, Quiz.DoesNotExist, Flashcard.DoesNotExist):
        return Response({"error": "Content not found or access denied"}, status=404)
    
    # Validate group access for group-only links
    group = None
    if access_level == 'group':
        if not group_id:
            return Response({"error": "Group ID required for group-only access"}, status=400)
        try:
            group = StudyGroup.objects.get(id=group_id)
            if not GroupMembership.objects.filter(user=request.user, group=group).exists():
                return Response({"error": "You are not a member of this group"}, status=403)
        except StudyGroup.DoesNotExist:
            return Response({"error": "Group not found"}, status=404)
    
    # Create shared link (allow multiple links per content)
    shared_link = SharedLink.objects.create(
        content_type=content_type,
        content_id=content_id,
        access_level=access_level,
        group=group,
        created_by=request.user,
        title=title,
        description=description
    )
    
    serializer = SharedLinkSerializer(shared_link, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def access_shared_link(request, link_id):
    try:
        shared_link = SharedLink.objects.get(link_id=link_id)
    except SharedLink.DoesNotExist:
        return Response({"detail": "Shared link not found"}, status=404)
    
    # Check access permissions
    if shared_link.access_level == 'private':
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=401)
        if request.user != shared_link.created_by:
            return Response({"detail": "Access denied"}, status=403)
    
    elif shared_link.access_level == 'group':
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=401)
        if not GroupMembership.objects.filter(user=request.user, group=shared_link.group).exists():
            return Response({"detail": "Access denied"}, status=403)
    
    # Get the content
    try:
        if shared_link.content_type == 'note':
            content = Note.objects.get(id=shared_link.content_id)
            return Response({
                'title': content.title,
                'content': content.content,
                'notebook_title': content.notebook.title,
                'created_at': content.created_at
            })
        elif shared_link.content_type == 'quiz':
            quiz = Quiz.objects.get(id=shared_link.content_id)
            questions = Question.objects.filter(quiz=quiz)
            return Response({
                'quiz_id': quiz.id,
                'title': quiz.note.title,
                'note_title': quiz.note.title,
                'questions': [
                    {
                        'question': q.question,
                        'options': q.options,
                        'correct': q.correct
                    } for q in questions
                ]
            })
        elif shared_link.content_type == 'flashcard':
            content = Flashcard.objects.get(id=shared_link.content_id)
            return Response({
                'question': content.question,
                'answer': content.answer,
                'note_title': content.note.title
            })
        else:
            return Response({"detail": "Invalid content type"}, status=400)
    except (Note.DoesNotExist, Quiz.DoesNotExist, Flashcard.DoesNotExist):
        return Response({"detail": "Content not found"}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_shared_links(request):
    shared_links = SharedLink.objects.filter(created_by=request.user)
    serializer = SharedLinkSerializer(shared_links, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_shared_link(request, link_id):
    try:
        shared_link = SharedLink.objects.get(link_id=link_id, created_by=request.user)
    except SharedLink.DoesNotExist:
        return Response({"error": "Link not found or access denied"}, status=404)
    
    shared_link.delete()
    return Response({"message": "Link deleted successfully"})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_group_resource(request, resource_id):
    try:
        resource = GroupResource.objects.get(id=resource_id, shared_by=request.user)
    except GroupResource.DoesNotExist:
        return Response({"error": "Resource not found or access denied"}, status=404)
    
    resource.delete()
    return Response({"message": "Resource removed from group successfully"})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_shared_note_from_group(request, note_id, group_id):
    try:
        shared_note = SharedNote.objects.get(note_id=note_id, group_id=group_id, shared_by=request.user)
    except SharedNote.DoesNotExist:
        return Response({"error": "Shared note not found or access denied"}, status=404)
    
    shared_note.delete()
    return Response({"message": "Note removed from group successfully"})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_shared_quiz_from_group(request, quiz_id, group_id):
    try:
        shared_quiz = SharedQuiz.objects.get(quiz_id=quiz_id, group_id=group_id, shared_by=request.user)
    except SharedQuiz.DoesNotExist:
        return Response({"error": "Shared quiz not found or access denied"}, status=404)
    
    shared_quiz.delete()
    return Response({"message": "Quiz removed from group successfully"})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_shared_flashcard_from_group(request, flashcard_id, group_id):
    try:
        shared_flashcard = SharedFlashcard.objects.get(flashcard_id=flashcard_id, group_id=group_id, shared_by=request.user)
    except SharedFlashcard.DoesNotExist:
        return Response({"error": "Shared flashcard not found or access denied"}, status=404)
    
    shared_flashcard.delete()
    return Response({"message": "Flashcard removed from group successfully"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_group_chat(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    
    # Check if user is a member of the group
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    
    messages = ChatMessage.objects.filter(group=group)
    serializer = ChatMessageSerializer(messages, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_group_message(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    
    # Check if user is a member of the group
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    
    message = request.data.get('message')
    message_type = request.data.get('message_type', 'text')
    
    if not message:
        return Response({"error": "Message is required"}, status=400)
    
    # Create the chat message
    chat_message = ChatMessage.objects.create(
        group=group,
        user=request.user,
        message=message,
        message_type=message_type
    )
    
    serializer = ChatMessageSerializer(chat_message)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_group_resources(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    
    # Check if user is a member of the group
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    
    resources = GroupResource.objects.filter(group=group)
    result = []
    
    for resource in resources:
        # Find the corresponding shareable link
        shared_link = SharedLink.objects.filter(
            content_type=resource.resource_type,
            content_id=resource.resource_id,
            group=group
        ).first()
        
        if shared_link:
            resource_data = {
                "id": resource.id,  # GroupResource ID (for deletion)
                "resource_id": resource.resource_id,  # Original note/quiz/flashcard ID
                "type": resource.resource_type,
                "title": resource.title,
                "url": f"/shared/{shared_link.link_id}",
                "shareable_link_id": str(shared_link.link_id),
                "shared_by": {
                    "id": resource.shared_by.id,
                    "username": resource.shared_by.username,
                    "first_name": resource.shared_by.first_name,
                    "last_name": resource.shared_by.last_name
                },
                "shared_at": resource.shared_at.isoformat(),
                "likes_count": resource.likes_count,
                "is_liked": resource.is_liked_by(request.user)
            }
            result.append(resource_data)
        else:
            try:
                shared_link = SharedLink.objects.create(
                    content_type=resource.resource_type,
                    content_id=resource.resource_id,
                    access_level='group',
                    group=group,
                    created_by=resource.shared_by,
                    title=resource.title,
                    description=resource.description
                )
                resource_data = {
                    "id": resource.id,
                    "resource_id": resource.resource_id,
                    "type": resource.resource_type,
                    "title": resource.title,
                    "url": f"/shared/{shared_link.link_id}",
                    "shareable_link_id": str(shared_link.link_id),
                    "shared_by": {
                        "id": resource.shared_by.id,
                        "username": resource.shared_by.username,
                        "first_name": resource.shared_by.first_name,
                        "last_name": resource.shared_by.last_name
                    },
                    "shared_at": resource.shared_at.isoformat(),
                    "likes_count": resource.likes_count,
                    "is_liked": resource.is_liked_by(request.user)
                }
                result.append(resource_data)
            except Exception as e:
                continue
    
    return Response(result)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_resource_to_group(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    
    # Check if user is a member of the group
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    
    resource_type = request.data.get('type')
    resource_id = request.data.get('resource_id')
    title = request.data.get('title', '')
    description = request.data.get('description', '')
    
    if not resource_type or not resource_id:
        return Response({"error": "Type and resource_id are required"}, status=400)
    
    # Validate resource type
    if resource_type not in ['note', 'quiz', 'flashcard']:
        return Response({"error": "Invalid resource type"}, status=400)
    
    # Check if user owns the resource
    try:
        if resource_type == 'note':
            resource = Note.objects.get(id=resource_id, notebook__user=request.user)
        elif resource_type == 'quiz':
            resource = Quiz.objects.get(id=resource_id, note__notebook__user=request.user)
        elif resource_type == 'flashcard':
            resource = Flashcard.objects.get(id=resource_id, note__notebook__user=request.user)
    except (Note.DoesNotExist, Quiz.DoesNotExist, Flashcard.DoesNotExist):
        return Response({"error": "Resource not found or access denied"}, status=404)
    
    # Check if already shared
    if GroupResource.objects.filter(group=group, resource_type=resource_type, resource_id=resource_id).exists():
        return Response({"error": "Resource already shared with this group"}, status=400)
    
    # Create the shared resource
    group_resource = GroupResource.objects.create(
        group=group,
        shared_by=request.user,
        resource_type=resource_type,
        resource_id=resource_id,
        title=title,
        description=description
    )
    
    # Create a shareable link for this resource
    shared_link = SharedLink.objects.create(
        content_type=resource_type,
        content_id=resource_id,
        access_level='group',
        group=group,
        created_by=request.user,
        title=title,
        description=description
    )
    
    # Return the resource data with shareable link info
    resource_data = {
        "id": resource_id,
        "type": resource_type,
        "title": title,
        "url": f"/shared/{shared_link.link_id}",
        "shareable_link_id": str(shared_link.link_id),
        "shared_by": {
            "id": request.user.id,
            "username": request.user.username,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name
        },
        "shared_at": group_resource.shared_at.isoformat(),
        "likes_count": 0,
        "is_liked": False
    }
    
    return Response(resource_data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_resource(request, resource_id):
    try:
        resource = GroupResource.objects.get(id=resource_id)
    except GroupResource.DoesNotExist:
        return Response({"error": "Resource not found"}, status=404)
    
    # Check if user is a member of the group
    if not GroupMembership.objects.filter(user=request.user, group=resource.group).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
    
    # Toggle like
    like, created = ResourceLike.objects.get_or_create(
        resource=resource,
        user=request.user
    )
    
    if not created:
        # Unlike if already liked
        like.delete()
    
    serializer = GroupResourceSerializer(resource, context={'request': request})
    return Response(serializer.data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_group(request, group_id):
    try:
        group = StudyGroup.objects.get(id=group_id)
    except StudyGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)
    
    # Only superusers can delete groups
    if not request.user.is_superuser:
        return Response({"error": "Only superusers can delete groups"}, status=403)
    
    # Delete the group (this will cascade delete all memberships, chat messages, shared content, etc.)
    group.delete()
    return Response({"message": "Group deleted successfully"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_pending_invitations(request):
    invitations = GroupInvitation.objects.filter(invited_user=request.user, status='pending')
    serializer = GroupInvitationSerializer(invitations, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_invitation(request, invitation_id):
    try:
        invitation = GroupInvitation.objects.get(id=invitation_id, invited_user=request.user)
    except GroupInvitation.DoesNotExist:
        return Response({"error": "Invitation not found"}, status=404)
    if invitation.status != 'pending':
        return Response({"error": "Invitation already responded to"}, status=400)
    group = invitation.group
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        GroupMembership.objects.create(user=request.user, group=group, role='member')
    invitation.status = 'accepted'
    invitation.save()
    return Response({"message": "Invitation accepted"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_invitation(request, invitation_id):
    try:
        invitation = GroupInvitation.objects.get(id=invitation_id, invited_user=request.user)
    except GroupInvitation.DoesNotExist:
        return Response({"error": "Invitation not found"}, status=404)
    if invitation.status != 'pending':
        return Response({"error": "Invitation already responded to"}, status=400)
    invitation.status = 'declined'
    invitation.save()
    return Response({"message": "Invitation declined"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_all_groups(request):
    # Check if user is superuser
    if not request.user.is_superuser:
        return Response({"error": "Superuser access required"}, status=403)
    
    groups = StudyGroup.objects.all()
    group_data = []
    
    for group in groups:
        member_count = GroupMembership.objects.filter(group=group).count()
        is_member = GroupMembership.objects.filter(user=request.user, group=group).exists()
        
        group_data.append({
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'public': group.public,
            'member_count': member_count,
            'created_by': {
                'id': group.created_by.id,
                'username': group.created_by.username,
                'first_name': group.created_by.first_name,
                'last_name': group.created_by.last_name
            },
            'created_at': group.created_at,
            'is_member': is_member
        })
    
    return Response(group_data)