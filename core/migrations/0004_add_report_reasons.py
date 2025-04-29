from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_update_report_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='reason',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('inappropriate', 'Inappropriate Content'),
                    ('copyright', 'Copyright Violation'),
                    ('harmful', 'Harmful or Dangerous'),
                    ('misinformation', 'Misinformation'),
                    ('hate_speech', 'Hate Speech'),
                    ('harassment', 'Harassment or Bullying'),
                    ('spam', 'Spam or Misleading'),
                    ('violence', 'Violent or Graphic Content'),
                    ('adult', 'Adult/Sexual Content'),
                    ('child_safety', 'Child Safety Concern'),
                    ('terrorism', 'Terrorism/Extremism'),
                    ('illegal_activity', 'Illegal Activity'),
                    ('impersonation', 'Impersonation'),
                    ('privacy', 'Privacy Violation'),
                    ('false_information', 'False Information'),
                    ('self_harm', 'Self-Harm Content'),
                    ('trademark', 'Trademark Violation'),
                    ('other', 'Other')
                ]
            ),
        ),
    ] 