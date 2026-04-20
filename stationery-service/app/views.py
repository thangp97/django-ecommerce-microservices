from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Stationery
from .serializers import StationerySerializer


class StationeryListCreate(APIView):
    def get(self, request):
        items = Stationery.objects.all()
        return Response(StationerySerializer(items, many=True).data)

    def post(self, request):
        serializer = StationerySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class StationeryDetail(APIView):
    def get(self, request, pk):
        try:
            item = Stationery.objects.get(pk=pk)
            return Response(StationerySerializer(item).data)
        except Stationery.DoesNotExist:
            return Response({'error': 'Stationery not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = Stationery.objects.get(pk=pk)
            serializer = StationerySerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Stationery.DoesNotExist:
            return Response({'error': 'Stationery not found'}, status=404)


class StationeryReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = Stationery.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Stationery.DoesNotExist:
            return Response({'error': 'Stationery không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class StationeryRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = Stationery.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Stationery.DoesNotExist:
            return Response({'error': 'Stationery không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
