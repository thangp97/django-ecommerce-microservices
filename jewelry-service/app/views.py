from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Jewelry
from .serializers import JewelrySerializer


class JewelryListCreate(APIView):
    def get(self, request):
        items = Jewelry.objects.all()
        return Response(JewelrySerializer(items, many=True).data)

    def post(self, request):
        serializer = JewelrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class JewelryDetail(APIView):
    def get(self, request, pk):
        try:
            item = Jewelry.objects.get(pk=pk)
            return Response(JewelrySerializer(item).data)
        except Jewelry.DoesNotExist:
            return Response({'error': 'Jewelry not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = Jewelry.objects.get(pk=pk)
            serializer = JewelrySerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Jewelry.DoesNotExist:
            return Response({'error': 'Jewelry not found'}, status=404)


class JewelryReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = Jewelry.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Jewelry.DoesNotExist:
            return Response({'error': 'Jewelry không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class JewelryRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = Jewelry.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Jewelry.DoesNotExist:
            return Response({'error': 'Jewelry không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
