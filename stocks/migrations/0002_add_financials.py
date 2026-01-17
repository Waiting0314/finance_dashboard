from django.db import models, migrations

class Migration(migrations.Migration):
    dependencies = [('stocks', '0001_initial')]  # Adjust dependency as needed (check migrations file)

    operations = [
        migrations.AddField(
            model_name='stock',
            name='last_revenue',
            field=models.BigIntegerField(null=True, blank=True, help_text="營收"),
        ),
        migrations.AddField(
            model_name='stock',
            name='next_earnings_date',
            field=models.DateTimeField(null=True, blank=True, help_text="下次財報日期"),
        ),
    ]
