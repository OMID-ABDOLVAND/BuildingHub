from django.core.management.base import BaseCommand

from subscriptions.services import process_subscription_lifecycle


class Command(BaseCommand):
    help = "Process subscription expiration, grace period, and related notifications"

    def handle(self, *args, **options):
        stats = process_subscription_lifecycle()
        self.stdout.write(self.style.SUCCESS("Subscription lifecycle processed."))
        for key, value in stats.items():
            self.stdout.write(f"  {key}: {value}")
