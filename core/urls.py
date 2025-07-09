from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotebookViewSet, NoteViewSet, FlashcardViewSet, QuizViewSet, QuestionViewSet, generate_quiz, get_quiz


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
    path('get_quiz/<int:note_id>/', get_quiz, name='generate_quiz'),
]