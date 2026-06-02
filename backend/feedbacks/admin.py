from django.contrib import admin
from feedbacks.models import Feedback

class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'occurrence', 'rating', 'created_at',)

admin.site.register(Feedback, FeedbackAdmin)
