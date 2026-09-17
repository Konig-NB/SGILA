"""Central account and learner access decisions used by web and API views."""

from .models import Parent, Subscription


ACCESS_PARENT_DEACTIVATED = 'parent_deactivated'
ACCESS_TEACHER_DEACTIVATED = 'teacher_deactivated'
ACCESS_LEARNER_DEACTIVATED = 'learner_deactivated'
ACCESS_SUBSCRIPTION_INACTIVE = 'subscription_inactive'


def linked_parent_for_child(child):
    """Resolve modern FK links first, then support legacy parent-email links."""
    if child.parent_id:
        return child.parent
    parent_email = (child.parent_email or '').strip()
    if not parent_email:
        return None
    return Parent.objects.filter(email__iexact=parent_email).first()


def subscription_allows_children(parent):
    """Treat legacy accounts without a Subscription row as trial accounts."""
    subscription = Subscription.objects.filter(parent=parent).only('status').first()
    if not subscription:
        return True
    return subscription.status in {'trial', 'active'}


def child_access_status(child):
    parent = linked_parent_for_child(child)
    if parent and not parent.is_active:
        return False, ACCESS_PARENT_DEACTIVATED
    if not child.is_active:
        return False, ACCESS_LEARNER_DEACTIVATED
    if parent and not subscription_allows_children(parent):
        return False, ACCESS_SUBSCRIPTION_INACTIVE
    return True, ''


def teacher_access_status(teacher):
    if not teacher.is_active:
        return False, ACCESS_TEACHER_DEACTIVATED
    return True, ''
