from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Toy
from .serializers import ToySerializer


class ToyListCreate(APIView):
    def get(self, request):
        items = Toy.objects.all()
        return Response(ToySerializer(items, many=True).data)

    def post(self, request):
        serializer = ToySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ToyDetail(APIView):
    def get(self, request, pk):
        try:
            item = Toy.objects.get(pk=pk)
            return Response(ToySerializer(item).data)
        except Toy.DoesNotExist:
            return Response({'error': 'Toy not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = Toy.objects.get(pk=pk)
            serializer = ToySerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Toy.DoesNotExist:
            return Response({'error': 'Toy not found'}, status=404)


class ToyReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = Toy.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Toy.DoesNotExist:
            return Response({'error': 'Toy không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ToyRestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = Toy.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except Toy.DoesNotExist:
            return Response({'error': 'Toy không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
