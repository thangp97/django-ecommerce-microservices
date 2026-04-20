from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Food
from .serializers import FoodSerializer


class FoodListCreate(APIView):
    def get(self, request):
        items = Food.objects.all()
        return Response(FoodSerializer(items, many=True).data)

    def post(self, request):
        serializer = FoodSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class FoodDetail(APIView):
    def get(self, request, pk):
        try:
            item = Food.objects.get(pk=pk)
            return Response(FoodSerializer(item).data)
        except Food.DoesNotExist:
            return Response({'error': 'Food not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = Food.objects.get(pk=pk)
            serializer = FoodSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Food.DoesNotExist:
            return Response({'error': 'Food not found'}, status=404)


class FoodReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = Food.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Food.DoesNotExist:
            return Response({'error': 'Food không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class FoodRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = Food.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Food.DoesNotExist:
            return Response({'error': 'Food không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
