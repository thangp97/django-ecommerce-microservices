from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Cosmetic
from .serializers import CosmeticSerializer


class CosmeticListCreate(APIView):
    def get(self, request):
        items = Cosmetic.objects.all()
        return Response(CosmeticSerializer(items, many=True).data)

    def post(self, request):
        serializer = CosmeticSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class CosmeticDetail(APIView):
    def get(self, request, pk):
        try:
            item = Cosmetic.objects.get(pk=pk)
            return Response(CosmeticSerializer(item).data)
        except Cosmetic.DoesNotExist:
            return Response({'error': 'Cosmetic not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = Cosmetic.objects.get(pk=pk)
            serializer = CosmeticSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Cosmetic.DoesNotExist:
            return Response({'error': 'Cosmetic not found'}, status=404)


class CosmeticReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = Cosmetic.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Cosmetic.DoesNotExist:
            return Response({'error': 'Cosmetic không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class CosmeticRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = Cosmetic.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Cosmetic.DoesNotExist:
            return Response({'error': 'Cosmetic không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
