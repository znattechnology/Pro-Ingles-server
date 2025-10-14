# Generated manually for missing quiz_data and practice_selection fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0009_remove_price_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='chapter',
            name='quiz_data',
            field=models.JSONField(blank=True, help_text='Quiz questions and settings data (JSON format)', null=True),
        ),
        migrations.AddField(
            model_name='chapter',
            name='practice_selection',
            field=models.JSONField(blank=True, help_text='Practice course selection data for exercise chapters', null=True),
        ),
    ]