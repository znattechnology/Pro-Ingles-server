from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import F

from .models import IntegrationProvider, IntegrationLog, APIQuota
from .serializers import *
from .services import *


class IntegrationProviderListView(generics.ListAPIView):
    queryset = IntegrationProvider.objects.filter(status='active')
    serializer_class = IntegrationProviderSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_sms_view(request):
    serializer = SMSMessageSerializer(data=request.data)
    if serializer.is_valid():
        success = send_sms(
            serializer.validated_data['to_phone'],
            serializer.validated_data['message'],
            request.user
        )
        return Response({'success': success})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def geocode_view(request):
    serializer = GeocodeRequestSerializer(data=request.data)
    if serializer.is_valid():
        location = geocode_address(
            serializer.validated_data['address'],
            request.user
        )
        if location:
            return Response(LocationDataSerializer(location).data)
        return Response({'error': 'Geocoding failed'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def integration_stats(request):
    today = timezone.now().date()
    stats = {
        'total_providers': IntegrationProvider.objects.count(),
        'active_providers': IntegrationProvider.objects.filter(status='active').count(),
        'total_requests_today': IntegrationLog.objects.filter(created_at__date=today).count(),
    }
    return Response(stats)
