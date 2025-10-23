from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import VideoEntry
import json

def index(request):
    videos = VideoEntry.objects.all()
    return render(request, 'collector/index.html', {'videos': videos})

@csrf_exempt
def update_selection(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        video_id = data.get('id')
        selected = data.get('selected')

        try:
            video = VideoEntry.objects.get(id=video_id)
            video.selected = selected
            video.save()
            return JsonResponse({'status': 'success'})
        except VideoEntry.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Video nicht gefunden'})

    return JsonResponse({'status': 'error', 'message': 'Ungültige Anfrage'})
