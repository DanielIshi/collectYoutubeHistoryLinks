from django.db import models

class VideoEntry(models.Model):
    url = models.URLField(unique=True)
    title = models.CharField(max_length=500)
    score = models.FloatField()
    method = models.CharField(max_length=20)
    selected = models.BooleanField(default=True)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
