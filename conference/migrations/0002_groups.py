from django.db import migrations


def create_groups(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    session_type, _ = ContentType.objects.get_or_create(app_label="conference", model="session")
    chatlog_type, _ = ContentType.objects.get_or_create(app_label="conference", model="chatlog")
    view_session, _ = Permission.objects.get_or_create(
        codename="view_session",
        content_type=session_type,
        defaults={"name": "Can view session"},
    )
    view_analytics, _ = Permission.objects.get_or_create(
        codename="view_analytics",
        content_type=chatlog_type,
        defaults={"name": "Може переглядати аналітику чату події"},
    )

    attendee, _ = Group.objects.get_or_create(name="attendee")
    attendee.permissions.add(view_session)
    organizer, _ = Group.objects.get_or_create(name="organizer")
    organizer.permissions.add(view_session, view_analytics)


def remove_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["attendee", "organizer"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("conference", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
