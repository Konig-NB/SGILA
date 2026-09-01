"""
Emails parents whose children are due a yearly grade confirmation.

This command is scheduler-agnostic on purpose — run it however suits your
hosting setup (cron, Windows Task Scheduler, a platform's built-in scheduler,
or just by hand). It's safe to run as often as you like: each parent gets at
most one reminder email per school year, tracked via
Child.grade_reminder_sent_year, so re-running it daily won't spam anyone.

Usage:
    python manage.py send_grade_reminders            # send real emails
    python manage.py send_grade_reminders --dry-run   # preview, sends nothing
"""
from collections import defaultdict

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from api.models import Child, current_school_year


class Command(BaseCommand):
    help = "Email parents whose children need their yearly grade confirmed."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Show who would be emailed without actually sending anything.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        year = current_school_year()

        due_children = [
            child for child in Child.objects.select_related('parent').all()
            if child.needs_grade_confirmation() and not child.reminder_already_sent_this_year()
        ]

        if not due_children:
            self.stdout.write("No reminders to send — everyone is confirmed or already reminded this year.")
            return

        # One email per parent, even if they have several children due — group by parent email.
        children_by_parent_email = defaultdict(list)
        for child in due_children:
            children_by_parent_email[child.parent_email].append(child)

        sent_count = 0
        for parent_email, children in children_by_parent_email.items():
            if not parent_email:
                self.stdout.write(self.style.WARNING(
                    f"Skipping {', '.join(c.name for c in children)} — no parent email on file."
                ))
                continue

            subject, message = build_reminder_email(children, year)

            if dry_run:
                self.stdout.write(f"[DRY RUN] Would email {parent_email}: {[c.name for c in children]}")
            else:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [parent_email], fail_silently=False)
                for child in children:
                    child.mark_reminder_sent()
                sent_count += len(children)
                self.stdout.write(f"Emailed {parent_email} about {[c.name for c in children]}")

        if dry_run:
            total = sum(len(c) for c in children_by_parent_email.values())
            self.stdout.write(self.style.SUCCESS(f"Dry run complete — {total} learner(s) across {len(children_by_parent_email)} parent(s) would be reminded."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done — reminded {len(children_by_parent_email)} parent(s) about {sent_count} learner(s)."))


def build_reminder_email(children, year):
    """Builds the subject/body for one parent's reminder. Never includes a
    one-click grade-change link — the parent must log in to confirm, so the
    change always goes through the normal authenticated, logged flow."""
    if len(children) == 1:
        child = children[0]
        subject = f"Quick check: what grade is {child.name} in this year?"
        names_line = f"{child.name} was in Grade {child.grade} last year."
    else:
        subject = "Quick check: what grade are your children in this year?"
        names_line = "\n".join(f"- {c.name} was in Grade {c.grade} last year." for c in children)

    message = (
        f"Hi there,\n\n"
        f"It's a new school year on SGILA ({year}), and we'd like to make sure your "
        f"child's lessons match the grade they're actually in at school.\n\n"
        f"{names_line}\n\n"
        f"SGILA never changes this automatically — only you (or your child's teacher) "
        f"can confirm it, so please log in and let us know, even if they're staying in "
        f"the same grade again this year:\n\n"
        f"  {settings.SITE_URL}/login\n\n"
        f"Once you're logged in, you'll see a banner on your dashboard with a grade "
        f"to confirm for each child.\n\n"
        f"— The SGILA Team"
    )
    return subject, message
