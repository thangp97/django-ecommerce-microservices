from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Appliance
from .serializers import ApplianceSerializer


class ApplianceListCreate(APIView):
    def get(self, request):
        items = Appliance.objects.all()
        return Response(ApplianceSerializer(items, many=True).data)

    def post(self, request):
        serializer = ApplianceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ApplianceDetail(APIView):
    def get(self, request, pk):
        try:
            item = Appliance.objects.get(pk=pk)
            return Response(ApplianceSerializer(item).data)
        except Appliance.DoesNotExist:
            return Response({'error': 'Appliance not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = Appliance.objects.get(pk=pk)
            serializer = ApplianceSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Appliance.DoesNotExist:
            return Response({'error': 'Appliance not found'}, status=404)


class ApplianceReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = Appliance.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Appliance.DoesNotExist:
            return Response({'error': 'Appliance không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ApplianceRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = Appliance.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Appliance.DoesNotExist:
            return Response({'error': 'Appliance không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
