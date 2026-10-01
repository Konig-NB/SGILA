from rest_framework import serializers

from .models import Feedback, HelpArticle, HelpCategory, SupportTicket


class HelpCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpCategory
        fields = ('id', 'name', 'slug', 'description', 'icon_name', 'order')


class HelpArticleSerializer(serializers.ModelSerializer):
    category = HelpCategorySerializer(read_only=True)

    class Meta:
        model = HelpArticle
        fields = (
            'id', 'title', 'slug', 'audience', 'content',
            'video_tutorial_url', 'is_kid_friendly', 'category',
        )


class SupportTicketSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    description = serializers.CharField(max_length=10000)
    email_notifications_sent = serializers.SerializerMethodField()
    support_notification_sent = serializers.SerializerMethodField()
    confirmation_email_sent = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = (
            'id', 'user', 'email', 'subject', 'issue_category',
            'description', 'status', 'created_at', 'email_notifications_sent',
            'support_notification_sent', 'confirmation_email_sent',
        )
        read_only_fields = ('id', 'user', 'status', 'created_at')

    def get_email_notifications_sent(self, obj):
        return getattr(obj, 'email_notifications_sent', False)

    def get_support_notification_sent(self, obj):
        return getattr(obj, 'support_notification_sent', False)

    def get_confirmation_email_sent(self, obj):
        return getattr(obj, 'confirmation_email_sent', False)

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        email = attrs.get('email', '')
        if not email and user and user.is_authenticated:
            email = user.email
            attrs['email'] = email
        if not email:
            raise serializers.ValidationError({'email': 'An email address is required for support follow-up.'})
        return attrs


class FeedbackSerializer(serializers.ModelSerializer):
    support_notification_sent = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = (
            'id', 'user_email', 'user_role', 'issue_category', 'subject',
            'message_body', 'created_at', 'support_notification_sent',
        )
        read_only_fields = ('id', 'created_at', 'support_notification_sent')

    def get_support_notification_sent(self, obj):
        return getattr(obj, 'support_notification_sent', False)
