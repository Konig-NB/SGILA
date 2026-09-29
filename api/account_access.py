"""Central account and learner access decisions used by web and API views."""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Child, Parent, Subscription


ACCESS_PARENT_DEACTIVATED = 'parent_deactivated'
ACCESS_TEACHER_DEACTIVATED = 'teacher_deactivated'
ACCESS_LEARNER_DEACTIVATED = 'learner_deactivated'
ACCESS_SUBSCRIPTION_INACTIVE = 'subscription_inactive'
CHILD_REASSIGNMENT_COOLDOWN = timedelta(days=3)

# Base number of learners a plan allows active at once, before any paid
# extra seats (Subscription.extra_active_seats). None means uncapped.
PLAN_CHILD_CAPS = {
    'individual': 1,
    'family': 4,
    'enterprise': None,
}


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


def plan_active_child_cap(parent):
    """How many of this parent's children can be active at once, or None if
    uncapped. Accounts with no Subscription row yet (shouldn't normally
    happen now that one is created at registration, but covers legacy data)
    are treated as the family-trial default rather than left uncapped.
    """
    subscription = Subscription.objects.filter(parent=parent).only('plan_type', 'extra_active_seats').first()
    plan_type = subscription.plan_type if subscription else 'family'
    base_cap = PLAN_CHILD_CAPS.get(plan_type, PLAN_CHILD_CAPS['family'])
    if base_cap is None:
        return None
    extra_seats = subscription.extra_active_seats if subscription else 0
    return base_cap + extra_seats


def active_child_count(parent, exclude_child_id=None):
    queryset = Child.objects.filter(
        Q(parent=parent) | Q(parent_email__iexact=parent.email),
        is_active=True,
    ).distinct()
    if exclude_child_id is not None:
        queryset = queryset.exclude(id=exclude_child_id)
    return queryset.count()


def child_reassignment_cooldown_until(parent, child=None, now=None):
    """Return when a recently paused learner's seat can be reassigned, if
    that cooldown is the reason another learner cannot use available capacity.
    """
    cap = plan_active_child_cap(parent)
    if cap is None:
        return None

    exclude_id = child.id if child else None
    active_count = active_child_count(parent, exclude_child_id=exclude_id)
    if active_count >= cap:
        return None

    now = now or timezone.now()
    cutoff = now - CHILD_REASSIGNMENT_COOLDOWN
    cooling_children = Child.objects.filter(
        (Q(parent=parent) | Q(parent_email__iexact=parent.email)),
        is_active=False,
        deactivated_reason=Child.DEACTIVATED_MANUAL,
        deactivated_at__gt=cutoff,
    )
    if exclude_id is not None:
        cooling_children = cooling_children.exclude(id=exclude_id)
    cooling_children = cooling_children.distinct()

    cooling_count = cooling_children.count()
    if active_count + cooling_count < cap:
        return None

    required_expirations = active_count + cooling_count - cap + 1
    next_available_deactivation = cooling_children.order_by('deactivated_at').values_list(
        'deactivated_at', flat=True
    )[required_expirations - 1]
    return next_available_deactivation + CHILD_REASSIGNMENT_COOLDOWN


def can_activate_child(parent, child=None):
    """Whether one more of this parent's children can be made active right
    now. Pass the child being (re)activated so it doesn't count against its
    own slot if it happens to already be active.
    """
    cap = plan_active_child_cap(parent)
    if cap is None:
        return True
    exclude_id = child.id if child else None
    current_active = active_child_count(parent, exclude_child_id=exclude_id)
    if current_active >= cap:
        return False

    cutoff = timezone.now() - CHILD_REASSIGNMENT_COOLDOWN
    cooling_children = Child.objects.filter(
        (Q(parent=parent) | Q(parent_email__iexact=parent.email)),
        is_active=False,
        deactivated_reason=Child.DEACTIVATED_MANUAL,
        deactivated_at__gt=cutoff,
    )
    if exclude_id is not None:
        cooling_children = cooling_children.exclude(id=exclude_id)
    return current_active + cooling_children.distinct().count() < cap


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

