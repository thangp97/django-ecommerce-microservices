from rest_framework.views import APIView
from rest_framework.response import Response
from .models import PetSupply
from .serializers import PetSupplySerializer


class PetSupplyListCreate(APIView):
    def get(self, request):
        items = PetSupply.objects.all()
        return Response(PetSupplySerializer(items, many=True).data)

    def post(self, request):
        serializer = PetSupplySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class PetSupplyDetail(APIView):
    def get(self, request, pk):
        try:
            item = PetSupply.objects.get(pk=pk)
            return Response(PetSupplySerializer(item).data)
        except PetSupply.DoesNotExist:
            return Response({'error': 'PetSupply not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = PetSupply.objects.get(pk=pk)
            serializer = PetSupplySerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except PetSupply.DoesNotExist:
            return Response({'error': 'PetSupply not found'}, status=404)


class PetSupplyReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = PetSupply.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except PetSupply.DoesNotExist:
            return Response({'error': 'PetSupply không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class PetSupplyRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = PetSupply.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except PetSupply.DoesNotExist:
            return Response({'error': 'PetSupply không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
