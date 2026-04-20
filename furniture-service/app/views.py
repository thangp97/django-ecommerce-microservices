from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Furniture
from .serializers import FurnitureSerializer


class FurnitureListCreate(APIView):
    def get(self, request):
        items = Furniture.objects.all()
        return Response(FurnitureSerializer(items, many=True).data)

    def post(self, request):
        serializer = FurnitureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class FurnitureDetail(APIView):
    def get(self, request, pk):
        try:
            item = Furniture.objects.get(pk=pk)
            return Response(FurnitureSerializer(item).data)
        except Furniture.DoesNotExist:
            return Response({'error': 'Furniture not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = Furniture.objects.get(pk=pk)
            serializer = FurnitureSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Furniture.DoesNotExist:
            return Response({'error': 'Furniture not found'}, status=404)


class FurnitureReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = Furniture.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Furniture.DoesNotExist:
            return Response({'error': 'Furniture không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class FurnitureRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = Furniture.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Furniture.DoesNotExist:
            return Response({'error': 'Furniture không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
