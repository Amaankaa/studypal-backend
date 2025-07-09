from django.contrib import admin
from .models import User, Notebook, Note, Flashcard, Quiz, Question

admin.site.register(User)
admin.site.register(Notebook)
admin.site.register(Note)
admin.site.register(Flashcard)
admin.site.register(Quiz)
admin.site.register(Question)
