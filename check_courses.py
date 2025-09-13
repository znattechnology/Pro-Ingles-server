#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.courses.models import Course

print(f'Total de cursos: {Course.objects.count()}')
print(f'Cursos Published: {Course.objects.filter(status="Published").count()}')
print(f'Cursos Draft: {Course.objects.filter(status="Draft").count()}')
print('\nCursos por status:')
for course in Course.objects.all():
    print(f'- {course.title}: {course.status}')