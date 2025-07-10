from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotebookViewSet, NoteViewSet, FlashcardViewSet, QuizViewSet, QuestionViewSet, generate_quiz, get_quiz, register_user, user_profile, generate_flashcards, get_flashcards_for_note, get_quizzes


router = DefaultRouter()
router.register(r'notebooks', NotebookViewSet, basename='notebook')
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'flashcards', FlashcardViewSet, basename='flashcard')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'questions', QuestionViewSet, basename='question')

urlpatterns = [
    path('', include(router.urls)),
]

urlpatterns += [
    path('generate_quiz/<int:note_id>/', generate_quiz, name='generate_quiz'),
    path('get_quiz/<int:note_id>/', get_quiz, name='get_quiz'),
    path('register/', register_user, name='register_user'),
    path('profile/', user_profile, name='user_profile'),
    path('generate_flashcards/<int:note_id>/', generate_flashcards, name='generate_flashcards'),
    path('get_flashcards/<int:note_id>/', get_flashcards_for_note, name='get_flashcards_for_note'),
    path('get_quizzes/<int:note_id>/', get_quizzes, name='get_quizzes'),
]