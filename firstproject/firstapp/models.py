from django.db import models

# Create your models here.
class Menuitem(models.Model):
    name = models.CharField(max_length=255)
    price = models.IntegerField()

class Reservation(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    guest_count = models.IntegerField()
    reservation_time = models.DateField(auto_now=True)
    comments = models.CharField(max_length=1000)

from django.db import models

class TAform(models.Model):
    TA_ID = models.AutoField(primary_key=True)
    introduction = models.TextField()
    goals = models.TextField()
    materials = models.TextField()
    instructions = models.TextField()
    observation = models.TextField()
    tips = models.TextField()
    extensions = models.TextField()
    resources = models.TextField()
    comments = models.TextField()
    status_tracking = models.CharField(max_length=100)
    current_status = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.TA_ID} - {self.introduction[:30]}"  # Display part of the introduction