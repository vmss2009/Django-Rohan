from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('firstapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='taform',
            name='introduction',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='goals',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='materials',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='instructions',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='observation',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='tips',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='extensions',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='resources',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='comments',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='status_tracking',
            field=models.CharField(max_length=100, default=''),
        ),
        migrations.AddField(
            model_name='taform',
            name='current_status',
            field=models.CharField(max_length=100, default=''),
        ),
    ]