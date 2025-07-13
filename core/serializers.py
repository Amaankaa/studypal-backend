from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notebook, Note, Flashcard, Quiz, Question, StudyGroup, GroupMembership, SharedNote, SharedQuiz, SharedFlashcard, SharedLink, ChatMessage, GroupResource, ResourceLike, GroupInvitation

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
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_superuser')
        read_only_fields = ('id', 'username', 'email', 'is_superuser')

class StudyGroupSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')
    class Meta:
        model = StudyGroup
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'public']

class GroupMembershipSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    group = serializers.ReadOnlyField(source='group.name')
    class Meta:
        model = GroupMembership
        fields = ['id', 'user', 'group', 'role', 'joined_at']

class SharedNoteSerializer(serializers.ModelSerializer):
    note_title = serializers.ReadOnlyField(source='note.title')
    shared_by_username = serializers.ReadOnlyField(source='shared_by.username')
    group_name = serializers.ReadOnlyField(source='group.name')
    
    class Meta:
        model = SharedNote
        fields = ['id', 'note', 'note_title', 'group', 'group_name', 'shared_by', 'shared_by_username', 'shared_at']

class SharedQuizSerializer(serializers.ModelSerializer):
    quiz_id = serializers.ReadOnlyField(source='quiz.id')
    shared_by_username = serializers.ReadOnlyField(source='shared_by.username')
    group_name = serializers.ReadOnlyField(source='group.name')
    
    class Meta:
        model = SharedQuiz
        fields = ['id', 'quiz', 'quiz_id', 'group', 'group_name', 'shared_by', 'shared_by_username', 'shared_at']

class SharedFlashcardSerializer(serializers.ModelSerializer):
    flashcard_question = serializers.ReadOnlyField(source='flashcard.question')
    shared_by_username = serializers.ReadOnlyField(source='shared_by.username')
    group_name = serializers.ReadOnlyField(source='group.name')
    
    class Meta:
        model = SharedFlashcard
        fields = ['id', 'flashcard', 'flashcard_question', 'group', 'group_name', 'shared_by', 'shared_by_username', 'shared_at']

class SharedLinkSerializer(serializers.ModelSerializer):
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    group_name = serializers.ReadOnlyField(source='group.name')
    full_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedLink
        fields = ['id', 'link_id', 'content_type', 'content_id', 'access_level', 'group', 'group_name', 'created_by', 'created_by_username', 'created_at', 'title', 'description', 'full_url']
    
    def get_full_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/shared/{obj.link_id}/')
        return f'/api/shared/{obj.link_id}/'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

class ChatMessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    resource_data = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'user', 'message', 'created_at', 'message_type', 'resource_data']
    
    def get_resource_data(self, obj):
        if obj.message_type == 'resource' and obj.resource_type and obj.resource_id:
            return {
                "type": obj.resource_type,
                "title": obj.resource_title,
                "id": obj.resource_id,
                "url": f"/api/{obj.resource_type}s/{obj.resource_id}/"
            }
        return None

class GroupResourceSerializer(serializers.ModelSerializer):
    shared_by = UserSerializer(read_only=True)
    likes_count = serializers.ReadOnlyField()
    is_liked = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupResource
        fields = ['id', 'resource_type', 'title', 'description', 'shared_by', 'shared_at', 'url', 'likes_count', 'is_liked']
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_liked_by(request.user)
        return False
    
    def get_url(self, obj):
        return f"/api/{obj.resource_type}s/{obj.resource_id}/"
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['type'] = instance.resource_type  # Map resource_type to 'type' for frontend
        return data

class GroupInvitationSerializer(serializers.ModelSerializer):
    group = StudyGroupSerializer(read_only=True)
    invited_by = UserSerializer(read_only=True)

    class Meta:
        model = GroupInvitation
        fields = ['id', 'group', 'invited_by', 'created_at', 'status']