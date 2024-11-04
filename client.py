import os
import json
import base64
import uuid
from paho.mqtt.client import Client
from moviepy.editor import concatenate_videoclips, VideoFileClip

output_folder = "reconstructed_videos/"
os.makedirs(output_folder, exist_ok=True)

temp_folder = "temp_clips/"
os.makedirs(temp_folder, exist_ok=True)

segments_received = []
total_segments = 10
def on_connect(client, userdata, flags, rc):
    print("Client connected to MQTT Broker")
    client.subscribe(f'client/{client_id}/segments')

def on_message(client, userdata, msg):
    segment = json.loads(msg.payload.decode())
    segment_data = base64.b64decode(segment['data'])
    segment_file = os.path.join(temp_folder, f"{segment['segment_id']}.mp4")

    with open(segment_file, 'wb') as f:
        f.write(segment_data)
    segments_received.append(segment_file)
    
    reconstruct_video()

def reconstruct_video():
    clips = [VideoFileClip(segment) for segment in segments_received]
    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(os.path.join(output_folder, f"reconstructed_{uuid.uuid4()}.mp4"))
    print("Video reconstruction complete!")

client_id = str(uuid.uuid4())
mqtt_client = Client(client_id)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect("localhost", 1883, 60)
mqtt_client.publish("client/connected", client_id)
mqtt_client.loop_forever()
