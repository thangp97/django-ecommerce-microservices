from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Electronic
from .serializers import ElectronicSerializer


class ElectronicListCreate(APIView):
    def get(self, request):
        items = Electronic.objects.all()
        return Response(ElectronicSerializer(items, many=True).data)

    def post(self, request):
        serializer = ElectronicSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ElectronicDetail(APIView):
    def get(self, request, pk):
        try:
            item = Electronic.objects.get(pk=pk)
            return Response(ElectronicSerializer(item).data)
        except Electronic.DoesNotExist:
            return Response({'error': 'Electronic not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = Electronic.objects.get(pk=pk)
            serializer = ElectronicSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Electronic.DoesNotExist:
            return Response({'error': 'Electronic not found'}, status=404)


class ElectronicReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = Electronic.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Electronic.DoesNotExist:
            return Response({'error': 'Electronic không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ElectronicRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = Electronic.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Electronic.DoesNotExist:
            return Response({'error': 'Electronic không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
