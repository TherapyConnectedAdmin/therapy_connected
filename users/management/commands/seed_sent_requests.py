from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db.models import Q

from users.models import Connection


class Command(BaseCommand):
    help = "Seed a number of pending connection requests sent by a given user (by email or first/last name)."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Sender user email who will send requests')
        parser.add_argument('--first', help='Sender first name (case-insensitive exact match)')
        parser.add_argument('--last', help='Sender last name (case-insensitive exact match)')
        parser.add_argument('--count', type=int, default=10, help='How many pending requests to create (default: 10)')

    def handle(self, *args, **options):
        email = options.get('email')
        first = options.get('first')
        last = options.get('last')
        count = options['count']
        User = get_user_model()

        if not email and not (first and last):
            raise CommandError("Provide either --email or both --first and --last to identify the sender user")

        if email:
            sender = User.objects.filter(email=email).first()
            ident_desc = f"email {email}"
        else:
            candidates = User.objects.filter(first_name__iexact=first, last_name__iexact=last)
            if not candidates.exists():
                raise CommandError(f"User with name '{first} {last}' not found")
            if candidates.count() > 1:
                emails = ", ".join(candidates.values_list('email', flat=True))
                raise CommandError(f"Multiple users named '{first} {last}'. Disambiguate with --email. Candidates: {emails}")
            sender = candidates.first()
            ident_desc = f"name {first} {last}"

        if not sender:
            raise CommandError(f"User with {ident_desc} not found")

        # Exclude users who already have any connection/pending with the sender in either direction
        existing_rel_user_ids = set(Connection.objects.filter(
            Q(requester=sender) | Q(addressee=sender)
        ).values_list('requester_id', flat=True)) | set(Connection.objects.filter(
            Q(requester=sender) | Q(addressee=sender)
        ).values_list('addressee_id', flat=True))
        existing_rel_user_ids.discard(sender.id)

        targets = (User.objects
                   .exclude(id=sender.id)
                   .exclude(id__in=list(existing_rel_user_ids))
                   .order_by('-date_joined', 'id'))

        created = 0
        used_targets = []
        for addressee in targets[:count]:
            if Connection.objects.filter(requester=sender, addressee=addressee).exists():
                continue
            Connection.objects.create(requester=sender, addressee=addressee, status='pending')
            created += 1
            used_targets.append(addressee)

        # If not enough, create placeholder targets to receive requests
        if created < count:
            to_create = count - created
            for i in range(to_create):
                placeholder_email = f"seed-requestee-{sender.id}-{i+1}@example.com"
                if User.objects.filter(email=placeholder_email).exists():
                    addressee = User.objects.get(email=placeholder_email)
                else:
                    addressee = User.objects.create_user(
                        email=placeholder_email,
                        password=None,
                        first_name='Requestee',
                        last_name=str(i+1),
                    )
                if not Connection.objects.filter(requester=sender, addressee=addressee).exists():
                    Connection.objects.create(requester=sender, addressee=addressee, status='pending')
                    created += 1
                    used_targets.append(addressee)

        self.stdout.write(self.style.SUCCESS(
            f"Created {created} pending request(s) from {sender.email}."
        ))
        if used_targets:
            for u in used_targets:
                name = (f"{u.first_name} {u.last_name}".strip() or u.email)
                self.stdout.write(f" - to {name} <{u.email}>")
