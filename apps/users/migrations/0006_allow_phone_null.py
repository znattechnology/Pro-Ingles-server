"""
Migration to allow phone field to be null.
"""

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_improve_phone_validation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(
                blank=True, 
                null=True,
                help_text='Número de telefone no formato internacional (ex: +244912345678 para Angola)', 
                max_length=20, 
                validators=[django.core.validators.RegexValidator(
                    message="Número de telefone deve estar no formato internacional: '+244912345678' (Angola) ou '+351912345678' (Portugal).", 
                    regex='^\\+(?:[1-9]\\d{0,3})?[1-9]\\d{8,14}$'
                )]
            ),
        ),
    ]