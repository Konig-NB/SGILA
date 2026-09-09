from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import redirect

from api.account_access import child_access_status
from api.models import Child, Parent


class AccountAccessMiddleware:
    """Invalidate stale sessions as soon as an account loses access."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        role = request.session.get('account_role')
        account_id = request.session.get('account_id')

        if role == 'parent' and account_id:
            parent = Parent.objects.filter(pk=account_id).only('is_active').first()
            if not parent or not parent.is_active:
                request.session.flush()
                return self._blocked_response(request, 'parent_deactivated')

        if role == 'learner' and account_id:
            child = Child.objects.select_related('parent').filter(pk=account_id).first()
            if not child:
                request.session.flush()
                return self._blocked_response(request, 'learner_not_found')
            allowed, reason = child_access_status(child)
            if not allowed:
                request.session.flush()
                return self._blocked_response(request, reason)

        return self.get_response(request)

    @staticmethod
    def _blocked_response(request, reason):
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Account access is paused.',
                'access_blocked': True,
                'reason': reason,
            }, status=403)
        return redirect(f"/account-access?{urlencode({'reason': reason})}")
