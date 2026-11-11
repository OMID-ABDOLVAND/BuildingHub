from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Create or update the initial BuildingHub SUPER_ADMIN account securely"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--phone", default="")
        parser.add_argument("--first-name", default="سوپر")
        parser.add_argument("--last-name", default="ادمین")

    def handle(self, *args, **options):
        username = options["username"].strip()
        email = options["email"].strip()
        password = options["password"]
        if len(password) < 8:
            raise CommandError("رمز عبور باید حداقل ۸ کاراکتر باشد.")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": options["first_name"],
                "last_name": options["last_name"],
                "phone": options["phone"],
            },
        )
        user.email = email
        user.first_name = options["first_name"]
        user.last_name = options["last_name"]
        if options["phone"]:
            user.phone = options["phone"]
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.platform_role = User.PlatformRole.SUPER_ADMIN
        user.save()

        action = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"SUPER_ADMIN {action}: username={user.username} email={user.email}"
            )
        )
