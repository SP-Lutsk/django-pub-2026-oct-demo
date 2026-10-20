from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conference", "0002_groups"),
    ]

    operations = [
        migrations.AlterField(
            model_name="session",
            name="kind",
            field=models.CharField(
                choices=[
                    ("talk", "Доповідь"),
                    ("discussion", "Дискусія"),
                    ("student", "Виступи студентів"),
                    ("reference", "Технічний довідник"),
                ],
                max_length=20,
            ),
        ),
    ]
