from django.db import models

class Block(models.Model):
    latitude = models.DecimalField(max_digits=6, decimal_places=4)
    longitude = models.DecimalField(max_digits=6, decimal_places=4)
    name = models.CharField(max_length=100)
    resources = models.IntegerField(default=0)
    orders = models.IntegerField(default=0)

    def __str__(self):
        return str(self.name) + ": " + str(self.id)

class DriverLocation(models.Model):
    name = models.CharField(max_length=100, default="Alex")
    latitude = models.DecimalField(max_digits=6, decimal_places=4)
    longitude = models.DecimalField(max_digits=6, decimal_places=4)

    def __str__(self):
        return  self.name + ": " + str(self.id)