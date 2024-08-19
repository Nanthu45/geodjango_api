from django.db import models
from django.contrib.gis.db import models

# Model for save the CSV data
class CsvData(models.Model):
    time = models.TimeField()  
    latitude = models.FloatField()
    longitude = models.FloatField()
    course = models.FloatField()
    speed_kts = models.FloatField()
    speed_mph = models.FloatField()
    altitude_feet = models.FloatField()
    reporting_facility = models.CharField(max_length=255)


# Model for lat,long as PSQL geometry point
class Location(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    point = models.PointField(geography=True, srid=4326) 

    def save(self, *args, **kwargs):
        if not self.name and self.pk is None:
            super().save(*args, **kwargs) 
            self.name = f"Location {self.pk}"
            self.save(update_fields=['name']) 
        else:
            super().save(*args, **kwargs) 
    def __str__(self):
        return self.name or "Unnamed Location"
    
    
    
# Model for joining lat,long as PSQL geometry view
class Route(models.Model):
    name = models.CharField(max_length=100)
    path = models.LineStringField()  

    def __str__(self):
        return self.name













