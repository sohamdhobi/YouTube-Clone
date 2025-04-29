from django.core.management.base import BaseCommand
from users.models import AdminRole

class Command(BaseCommand):
    help = 'Creates default admin roles'

    def handle(self, *args, **kwargs):
        # Create Super Admin role
        super_admin, created = AdminRole.objects.get_or_create(
            level=1,
            defaults={
                'name': 'Super Admin',
                'description': 'Full access to all admin features',
                'can_manage_users': True,
                'can_manage_content': True,
                'can_manage_settings': True,
                'can_manage_admins': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Super Admin role'))
        else:
            self.stdout.write(self.style.WARNING(f'Super Admin role already exists'))
        
        # Create Moderator role
        moderator, created = AdminRole.objects.get_or_create(
            level=2,
            defaults={
                'name': 'Moderator',
                'description': 'Can manage users and content',
                'can_manage_users': True,
                'can_manage_content': True,
                'can_manage_settings': False,
                'can_manage_admins': False,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Moderator role'))
        else:
            self.stdout.write(self.style.WARNING(f'Moderator role already exists'))
        
        # Create Support Staff role
        support, created = AdminRole.objects.get_or_create(
            level=3,
            defaults={
                'name': 'Support Staff',
                'description': 'Can manage users',
                'can_manage_users': True,
                'can_manage_content': False,
                'can_manage_settings': False,
                'can_manage_admins': False,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Support Staff role'))
        else:
            self.stdout.write(self.style.WARNING(f'Support Staff role already exists')) 