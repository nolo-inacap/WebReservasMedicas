from django.db import models
from django.contrib.auth.models import User
from app.firebase_config import db  # Importar el cliente de Firestore

class Doctor(models.Model):
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    description = models.TextField()
    schedule = models.CharField(max_length=100)
    available = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        doc_ref = db.collection('Doctors').document(str(self.id))
        doc_ref.set({
            'name': self.name,
            'specialty': self.specialty,
            'description': self.description,
            'schedule': self.schedule,
            'available': self.available
        })

    def __str__(self):
        return self.name

class Appointment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        doc_ref = db.collection('appointments').document(str(self.id))
        doc_ref.set({
            'user': self.user.username,
            'doctor': self.doctor.name,
            'date_created': self.date_created
        })

    def __str__(self):
        return f'Cita con {self.doctor.name} por {self.user.username}'