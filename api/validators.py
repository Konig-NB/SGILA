import re

SPECIAL_CHARS_RE = re.compile(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?~`]')


def password_strength_errors(password):
    """Returns a list of unmet rules (empty list = password is strong enough)."""
    errors = []
    if len(password) < 8:
        errors.append('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must include at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        errors.append('Password must include at least one lowercase letter.')
    if not re.search(r'[0-9]', password):
        errors.append('Password must include at least one number.')
    if not SPECIAL_CHARS_RE.search(password):
        errors.append('Password must include at least one special character.')
    return errors