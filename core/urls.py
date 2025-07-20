from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotebookViewSet, NoteViewSet, FlashcardViewSet, QuizViewSet, QuestionViewSet, generate_quiz, get_quiz, register_user, user_profile, generate_flashcards, get_flashcards_for_note, get_quizzes, create_study_group, list_user_groups, join_group, leave_group, invite_to_group, list_group_members, search_groups, get_group_details, list_group_shared_content, share_note_with_group, share_quiz_with_group, share_flashcard_with_group, create_shared_link, list_user_shared_links, delete_shared_link, access_shared_link, get_group_chat, send_group_message, get_group_resources, share_resource_to_group, like_resource, delete_group_resource, delete_shared_note_from_group, delete_shared_quiz_from_group, delete_shared_flashcard_from_group, delete_group, list_pending_invitations, accept_invitation, decline_invitation, list_all_groups, generate_note, submit_quiz_attempt, submit_flashcard_attempt, get_quiz_stats, get_flashcard_stats, get_user_progress, get_leaderboard, get_user_points


router = DefaultRouter()
router.register(r'notebooks', NotebookViewSet, basename='notebook')
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'flashcards', FlashcardViewSet, basename='flashcard')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'questions', QuestionViewSet, basename='question')

urlpatterns = [
    path('notes/generate/', generate_note, name='generate_note'),
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
    path('groups/create/', create_study_group, name='create_study_group'),
    path('groups/', list_user_groups, name='list_user_groups'),
    path('groups/<int:group_id>/join/', join_group, name='join_group'),
    path('groups/<int:group_id>/leave/', leave_group, name='leave_group'),
    path('groups/<int:group_id>/invite/', invite_to_group, name='invite_to_group'),
    path('groups/<int:group_id>/members/', list_group_members, name='list_group_members'),
    path('groups/<int:group_id>/', get_group_details, name='get_group_details'),
    path('groups/<int:group_id>/delete/', delete_group, name='delete_group'),
    path('groups/<int:group_id>/shared-content/', list_group_shared_content, name='list_group_shared_content'),
    path('groups/<int:group_id>/chat/', get_group_chat, name='get_group_chat'),
    path('groups/<int:group_id>/chat/send/', send_group_message, name='send_group_message'),
    path('groups/<int:group_id>/resources/', get_group_resources, name='get_group_resources'),
    path('groups/<int:group_id>/resources/share/', share_resource_to_group, name='share_resource_to_group'),
    path('resources/<int:resource_id>/like/', like_resource, name='like_resource'),
    path('resources/<int:resource_id>/delete/', delete_group_resource, name='delete_group_resource'),
    path('notes/<int:note_id>/share/<int:group_id>/', share_note_with_group, name='share_note_with_group'),
    path('notes/<int:note_id>/unshare/<int:group_id>/', delete_shared_note_from_group, name='delete_shared_note_from_group'),
    path('quizzes/<int:quiz_id>/share/<int:group_id>/', share_quiz_with_group, name='share_quiz_with_group'),
    path('quizzes/<int:quiz_id>/unshare/<int:group_id>/', delete_shared_quiz_from_group, name='delete_shared_quiz_from_group'),
    path('flashcards/<int:flashcard_id>/share/<int:group_id>/', share_flashcard_with_group, name='share_flashcard_with_group'),
    path('flashcards/<int:flashcard_id>/unshare/<int:group_id>/', delete_shared_flashcard_from_group, name='delete_shared_flashcard_from_group'),
    path('shared-links/create/', create_shared_link, name='create_shared_link'),
    path('shared-links/', list_user_shared_links, name='list_user_shared_links'),
    path('shared-links/<uuid:link_id>/delete/', delete_shared_link, name='delete_shared_link'),
    path('shared/<uuid:link_id>/', access_shared_link, name='access_shared_link'),
    path('groups/search/', search_groups, name='search_groups'),
    path('invitations/pending/', list_pending_invitations, name='list_pending_invitations'),
    path('invitations/<int:invitation_id>/accept/', accept_invitation, name='accept_invitation'),
    path('invitations/<int:invitation_id>/decline/', decline_invitation, name='decline_invitation'),
    path('groups/all/', list_all_groups, name='list_all_groups'),
    path('quiz_attempts/', submit_quiz_attempt, name='submit_quiz_attempt'),
    path('flashcard_attempts/', submit_flashcard_attempt, name='submit_flashcard_attempt'),
    path('quiz_stats/<int:quiz_id>/', get_quiz_stats, name='get_quiz_stats'),
    path('flashcard_stats/<int:flashcard_id>/', get_flashcard_stats, name='get_flashcard_stats'),
    path('user/progress/', get_user_progress, name='get_user_progress'),
    path('leaderboard/', get_leaderboard, name='get_leaderboard'),
    path('user/points/', get_user_points, name='get_user_points'),
]