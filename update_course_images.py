#!/usr/bin/env python
"""
Script para atualizar as imagens dos cursos do laboratório com as imagens dos serviços
"""

import os
import sys
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.courses.models import Course

def update_course_images():
    """Atualiza as imagens dos cursos que têm practice_units com imagens dos serviços"""
    
    # Array de imagens dos serviços
    service_images = [
        '/service-1.jpg',
        '/service-2.jpg', 
        '/service-3.jpg',
        '/service-4.jpg',
        '/service-5.jpg',
        '/service-6.jpg'
    ]
    
    # Buscar cursos que têm practice_units (cursos do laboratório)
    laboratory_courses = Course.objects.filter(
        practice_units__isnull=False,
        status='Published'
    ).distinct()
    
    print(f"Encontrados {laboratory_courses.count()} cursos do laboratório para atualizar")
    
    updated_count = 0
    
    for course in laboratory_courses:
        # Função hash simples baseada no ID do curso
        course_id_str = str(course.id)
        hash_value = sum(ord(char) for char in course_id_str)
        image_index = hash_value % len(service_images)
        
        # Atualizar apenas se não tem imagem ou se a imagem atual não é uma das imagens de serviço
        current_image = course.image or ''
        if not current_image or not any(service_img in current_image for service_img in service_images):
            new_image = service_images[image_index]
            course.image = new_image
            course.save()
            
            print(f"✅ Curso '{course.title}' atualizado com imagem: {new_image}")
            updated_count += 1
        else:
            print(f"⚪ Curso '{course.title}' já possui imagem de serviço")
    
    print(f"\n🎉 Atualização concluída! {updated_count} cursos foram atualizados.")
    
    # Mostrar resultado final
    print("\n📋 Lista de cursos do laboratório:")
    for course in laboratory_courses:
        print(f"  - {course.title} ({course.level}) -> {course.image}")

if __name__ == '__main__':
    update_course_images()