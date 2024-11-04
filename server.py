import json
import random
import base64
import time
import requests
import os
import string
import uuid
import re

import paho.mqtt.client as mqtt
from moviepy.editor import VideoFileClip

def sanitize_filename(title):
    # Replace any invalid characters with an underscore
    return re.sub(r'[<>:"/\\|?*]', '_', title)

source_video_folder = "source_test_videos/"
clip_folder = "clips/"
avg_segments_per_video = 5
var_segments_per_video = 3

os.makedirs(source_video_folder, exist_ok=True)
os.makedirs(clip_folder, exist_ok=True)

with open('test_videos.json', 'r') as f:
    videos = json.load(f)['videos']

    for video in videos:
        title = video['title']
        url = video['sources'][0]
        sanitized_title = sanitize_filename(title)
        filename = os.path.join(source_video_folder, sanitized_title + '.mp4')
        #filename = os.path.join(source_video_folder, ''.join(filter(lambda x: x in set(string.printable), title)).replace(' ', '_') + '.mp4')
        print(f"Downloading {title} from {url} to {filename}")
        
        if not os.path.exists(filename):
            response = requests.get(url)
            with open(filename, 'wb') as f_video:
                f_video.write(response.content)
            
            video_file = VideoFileClip(filename)
            video_file = video_file.subclip(0, min(20, video_file.duration))
            video_file.write_videofile(filename, codec='libx264', audio_codec='aac', fps=24)
            video_file.close() 
            os.remove(filename)
            

for clip in os.listdir(clip_folder):
    os.remove(os.path.join(clip_folder, clip))

segments = []
for video in os.listdir(source_video_folder):
    video_path = os.path.join(source_video_folder, video)
    video_duration = float(os.popen(f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video_path}\"").read())
    
    num_segments = random.randint(avg_segments_per_video - var_segments_per_video, avg_segments_per_video + var_segments_per_video)

    start_times = [random.uniform(0, video_duration) for _ in range(num_segments)]
    start_times.sort()
    start_times[0] = 0

    pair_times = [(start_times[i], start_times[i+1]) for i in range(num_segments - 1)]
    pair_times.append((start_times[-1], video_duration))

    video_file = VideoFileClip(video_path)

    for start_time, end_time in pair_times:
        overlap = random.uniform(0, 0.1 * video_duration)
        new_end_time = min(end_time + overlap, video_duration)

        clip_id = str(uuid.uuid4())

        clip = video_file.subclip(start_time, new_end_time)
        clip.write_videofile(
            os.path.join(clip_folder, clip_id + '.mp4'),
            codec='libx264',
            audio_codec='aac',
            fps=24
        )

        segments.append({
            'segment_id': clip_id,
            'base_video': video,
            'base_video_duration': video_duration,
            'start_time': start_time,
            'end_time': new_end_time,
            'data': ''
        })
        
random.shuffle(segments)
print("Ready for solution connection!")

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Broker")
    client.subscribe('client/connected')

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    if topic == 'client/connected':
        client_id = payload
        print(f"Client connected: {client_id}")
        send_segments_to_client(client_id)

def send_segments_to_client(client_id):
    segments_copy = segments[:]
    random.shuffle(segments_copy)
    for segment in segments_copy:
        with open(os.path.join(clip_folder, segment['segment_id'] + '.mp4'), 'rb') as f:
            segment['data'] = base64.b64encode(f.read()).decode('utf-8')
        mqtt_client.publish(f'client/{client_id}/segments', json.dumps(segment))
        print(f"Sent segment {segment['segment_id']} to client {client_id}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_broker_host = 'localhost'
mqtt_broker_port = 1883

mqtt_client.connect(mqtt_broker_host, mqtt_broker_port, 60)

mqtt_client.loop_forever()