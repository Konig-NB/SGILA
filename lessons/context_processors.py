from django.db.models import Q


def unread_messages(request):
    """
    Makes `unread_messages_count` available in every template.
    Used by base.html to show a badge on the "Messages" nav link
    the moment a page loads (JS polling in base.html keeps it live
    after that, without needing a full page refresh).
    """
    role = request.session.get('account_role')
    account_id = request.session.get('account_id')

    if role not in ('parent', 'teacher') or not account_id:
        return {}

    # Imported here (not at module level) to avoid loading Django models
    # before the app registry is ready during startup.
    from api.models import Child, Message, Parent

    opposite_role = 'teacher' if role == 'parent' else 'parent'

    if role == 'parent':
        parent_email = Parent.objects.filter(pk=account_id).values_list('email', flat=True).first() or ''
        child_ids = Child.objects.filter(
            Q(parent_id=account_id) | Q(parent_email__iexact=parent_email)
        ).values_list('id', flat=True)
    else:
        child_ids = Child.objects.filter(teacher_id=account_id).values_list('id', flat=True)

    count = Message.objects.filter(
        child_id__in=child_ids, sender_role=opposite_role, is_read=False
    ).count()

    return {'unread_messages_count': count}
