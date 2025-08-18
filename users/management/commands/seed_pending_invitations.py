from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db.models import Q

from users.models import Connection


class Command(BaseCommand):
    help = "Seed a number of pending connection invitations targeting a given user (by email or first/last name)."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Target user email to receive invitations')
        parser.add_argument('--first', help='Target user first name (case-insensitive exact match)')
        parser.add_argument('--last', help='Target user last name (case-insensitive exact match)')
        parser.add_argument('--count', type=int, default=3, help='How many pending invitations to create (default: 3)')

    def handle(self, *args, **options):
        email = options.get('email')
        first = options.get('first')
        last = options.get('last')
        count = options['count']
        User = get_user_model()

        if not email and not (first and last):
            raise CommandError("Provide either --email or both --first and --last to identify the user")

        if email:
            target = User.objects.filter(email=email).first()
            ident_desc = f"email {email}"
        else:
            # Case-insensitive exact match on first_name/last_name
            candidates = User.objects.filter(first_name__iexact=first, last_name__iexact=last)
            if not candidates.exists():
                raise CommandError(f"User with name '{first} {last}' not found")
            if candidates.count() > 1:
                emails = ", ".join(candidates.values_list('email', flat=True))
                raise CommandError(f"Multiple users named '{first} {last}'. Disambiguate with --email. Candidates: {emails}")
            target = candidates.first()
            ident_desc = f"name {first} {last}"

        if not target:
            raise CommandError(f"User with {ident_desc} not found")

        # Find existing users to use as requesters, excluding the target and any with existing connection state with the target.
        existing_rel_user_ids = set(Connection.objects.filter(
            Q(requester=target) | Q(addressee=target)
        ).values_list('requester_id', flat=True)) | set(Connection.objects.filter(
            Q(requester=target) | Q(addressee=target)
        ).values_list('addressee_id', flat=True))
        existing_rel_user_ids.discard(target.id)

        candidates = (User.objects
                      .exclude(id=target.id)
                      .exclude(id__in=list(existing_rel_user_ids))
                      .order_by('-date_joined', 'id'))

        created = 0
        used_requesters = []
        for requester in candidates[:count]:
            # Double-check uniqueness
            if Connection.objects.filter(requester=requester, addressee=target).exists():
                continue
            Connection.objects.create(requester=requester, addressee=target, status='pending')
            created += 1
            used_requesters.append(requester)

        # If not enough candidates, create minimal placeholder users and send from them.
        if created < count:
            to_create = count - created
            for i in range(to_create):
                placeholder_email = f"seed-inviter-{target.id}-{i+1}@example.com"
                # Avoid duplicating if somehow exists
                if User.objects.filter(email=placeholder_email).exists():
                    requester = User.objects.get(email=placeholder_email)
                else:
                    requester = User.objects.create_user(
                        email=placeholder_email,
                        password=None,
                        first_name='Inviter',
                        last_name=str(i+1),
                    )
                # Create pending invite
                if not Connection.objects.filter(requester=requester, addressee=target).exists():
                    Connection.objects.create(requester=requester, addressee=target, status='pending')
                    created += 1
                    used_requesters.append(requester)

        self.stdout.write(self.style.SUCCESS(
            f"Created {created} pending invitation(s) to {target.email}."
        ))
        if used_requesters:
            for u in used_requesters:
                name = (f"{u.first_name} {u.last_name}".strip() or u.email)
                self.stdout.write(f" - from {name} <{u.email}>")
