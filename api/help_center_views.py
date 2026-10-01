import logging
from urllib.parse import urlencode

from django.conf import settings
from django.db import connection
from django.core.mail import EmailMessage
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.shortcuts import render
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from .models import Feedback, HelpArticle, HelpCategory, SupportTicket
from .serializers import (
    FeedbackSerializer,
    HelpArticleSerializer,
    HelpCategorySerializer,
    SupportTicketSerializer,
)

logger = logging.getLogger(__name__)


def help_center_page(request):
    return render(request, 'help_center.html')


class HelpCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HelpCategory.objects.all().order_by('order', 'name')
    serializer_class = HelpCategorySerializer
    lookup_field = 'slug'
    permission_classes = (AllowAny,)


class HelpArticleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HelpArticleSerializer
    lookup_field = 'slug'
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = HelpArticle.objects.select_related('category').all()
        if self.action != 'list':
            return queryset
        audience = self.request.query_params.get('audience')
        allowed_audiences = {choice for choice, _label in HelpArticle.Audience.choices}
        if audience in allowed_audiences:
            if audience == HelpArticle.Audience.LEARNER:
                queryset = queryset.filter(audience=audience, is_kid_friendly=True)
            else:
                queryset = queryset.filter(audience=audience)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        query_text = self.request.query_params.get('q', '').strip()
        if query_text:
            if connection.vendor == 'postgresql':
                search_vector = (
                    SearchVector('title', weight='A', config='english')
                    + SearchVector('content', weight='B', config='english')
                )
                search_query = SearchQuery(query_text, search_type='websearch', config='english')
                queryset = (
                    queryset.annotate(search=search_vector)
                    .filter(search=search_query)
                    .annotate(rank=SearchRank(search_vector, search_query))
                    .order_by('-rank', 'title')
                )
            else:
                queryset = queryset.filter(
                    Q(title__icontains=query_text) | Q(content__icontains=query_text)
                ).order_by('title')
        return queryset


class SupportTicketViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'help_ticket'

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_authenticated:
            ticket = serializer.save(user=user, email=serializer.validated_data.get('email') or user.email)
        else:
            ticket = serializer.save(user=None)

        support_body = '\n'.join((
            f'Subject: {ticket.subject}',
            f'From: {ticket.email}',
            f'Issue: {ticket.get_issue_category_display()}',
            f'Ticket: #{ticket.pk}',
            '',
            ticket.description,
        ))
        reply_body = '\n'.join((
            'Hello,',
            '',
            f'We received your message about: {ticket.subject}',
            f'Reference: #{ticket.pk}',
            '',
            'The Sgila support team will follow up by email.',
            '',
            'While you wait, these quick guides may help:',
            '\n'.join((
                f'Sign-in and password help: {settings.SITE_URL.rstrip("/")}/help/?{urlencode({"audience": "parent", "q": "sign in"})}',
                f'Connect a learner to a teacher: {settings.SITE_URL.rstrip("/")}/help/?{urlencode({"audience": "parent", "q": "teacher code"})}',
                f'View learning progress: {settings.SITE_URL.rstrip("/")}/help/?{urlencode({"audience": "parent", "q": "progress"})}',
            )),
            '',
            'Your message:',
            ticket.description,
            '',
            'Sgila Support',
        ))

        support_sent = self._send_notification(
            subject=f'Sgila Help Center: {ticket.subject}',
            message=support_body,
            recipient=settings.SUPPORT_EMAIL,
            reply_to=ticket.email,
            ticket=ticket,
        )
        user_reply_sent = self._send_notification(
            subject=f'We received your Sgila support request (#{ticket.pk})',
            message=reply_body,
            recipient=ticket.email,
            ticket=ticket,
        )
        ticket.support_notification_sent = support_sent
        ticket.confirmation_email_sent = user_reply_sent
        ticket.email_notifications_sent = support_sent and user_reply_sent

    @staticmethod
    def _send_notification(*, subject, message, recipient, ticket, reply_to=None):
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            logger.warning(
                'Help Center ticket %s saved, but email delivery is unavailable because SMTP is not configured',
                ticket.pk,
            )
            return False
        try:
            email = EmailMessage(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                reply_to=[reply_to] if reply_to else None,
            )
            sent_count = email.send(fail_silently=False)
        except Exception:
            logger.exception(
                'Could not send Help Center ticket notification for ticket %s to %s',
                ticket.pk,
                recipient,
            )
            return False
        if sent_count != 1:
            logger.error(
                'Help Center ticket notification for ticket %s was not accepted for %s',
                ticket.pk,
                recipient,
            )
            return False
        return True


class FeedbackViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'feedback'

    def perform_create(self, serializer):
        feedback = serializer.save()
        message = '\n'.join((
            f'Feedback: {feedback.get_issue_category_display()}',
            f'From: {feedback.user_email} ({feedback.get_user_role_display()})',
            f'Subject: {feedback.subject}',
            f'Reference: #{feedback.pk}',
            '',
            feedback.message_body,
        ))
        feedback.support_notification_sent = self._send_notification(feedback, message)

    @staticmethod
    def _send_notification(feedback, message):
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            logger.warning(
                'Feedback %s saved, but notification email is unavailable because SMTP is not configured',
                feedback.pk,
            )
            return False
        try:
            email = EmailMessage(
                subject=f'Sgila feedback #{feedback.pk}: {feedback.subject}',
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.SUPPORT_EMAIL],
                reply_to=[feedback.user_email],
            )
            sent_count = email.send(fail_silently=False)
        except Exception:
            logger.exception('Could not send notification for feedback %s', feedback.pk)
            return False
        return sent_count == 1
