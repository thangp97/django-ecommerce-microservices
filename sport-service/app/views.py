from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Sport
from .serializers import SportSerializer


class SportListCreate(APIView):
    def get(self, request):
        items = Sport.objects.all()
        return Response(SportSerializer(items, many=True).data)

    def post(self, request):
        serializer = SportSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class SportDetail(APIView):
    def get(self, request, pk):
        try:
            item = Sport.objects.get(pk=pk)
            return Response(SportSerializer(item).data)
        except Sport.DoesNotExist:
            return Response({'error': 'Sport not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = Sport.objects.get(pk=pk)
            serializer = SportSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Sport.DoesNotExist:
            return Response({'error': 'Sport not found'}, status=404)


class SportReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = Sport.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Sport.DoesNotExist:
            return Response({'error': 'Sport không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class SportRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = Sport.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Sport.DoesNotExist:
            return Response({'error': 'Sport không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
