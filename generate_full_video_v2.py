import os
import sys
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration

prompt = """Cinematic healthcare promotional video with smooth professional animation:

SCENE 1 (0-3s): Dark blue space with scattered floating elements - a stethoscope (Allopathy), Ayurvedic herbs and mortar, lab report papers, pill bottles, yoga poses, heart rate monitors, and medical charts all floating chaotically, representing fragmented healthcare.

SCENE 2 (3-6s): A glowing golden light appears in the center. All the scattered elements begin flowing toward it, transforming into digital data streams - orange and teal colored light trails converging.

SCENE 3 (6-10s): The streams merge into a sleek smartphone showing the HealthTrack Pro app interface. Split screen shows: Left side - modern doctor in white coat (Allopathy), Right side - Ayurvedic practitioner with herbs. Both connected through the phone screen. AI neural network patterns pulse in the background.

SCENE 4 (10-14s): Zoom into the phone screen showing a unified health dashboard with: Lab results with AI analysis highlights, Ayurvedic dosha recommendations, medication schedules, wearable sync data, and a rising health score graph.

SCENE 5 (14-18s): Pull back to show a globe with glowing connection points across India, USA, Europe, Middle East - representing global service. Diverse families from different cultures all looking at their phones with the HealthTrack Pro app, smiling.

SCENE 6 (18-20s): Final frame - HealthTrack Pro logo with:
- "Visit us at infuse-ai.in"
- App Store and Play Store download icons
- "Create your account at infuse.net.in"
Orange gradient background with subtle health icons. Professional, premium healthcare aesthetic.

Style: Modern, cinematic, premium healthcare marketing. Color palette: Deep blue, orange (#E55A00), teal, gold accents. Smooth 24fps animation with elegant transitions. Professional medical aesthetic mixed with warm, approachable feel."""

print("=" * 60)
print("Starting FULL promotional video generation with Sora 2...")
print("Creating comprehensive HealthTrack Pro video (20 seconds)...")
print("This may take 8-12 minutes...")
print("=" * 60)

try:
    video_gen = OpenAIVideoGeneration(api_key=os.environ['EMERGENT_LLM_KEY'])
    
    video_bytes = video_gen.text_to_video(
        prompt=prompt,
        model="sora-2",
        size="1280x720",
        duration=12,  # Using max supported duration
        max_wait_time=900
    )
    
    if video_bytes:
        output_path = "/app/frontend/public/downloads/HealthTrackPro_Full_Promo_Video.mp4"
        video_gen.save_video(video_bytes, output_path)
        file_size = os.path.getsize(output_path) / 1024 / 1024
        print("=" * 60)
        print(f"SUCCESS: Video saved to: {output_path}")
        print(f"File size: {file_size:.2f} MB")
        print("=" * 60)
    else:
        print("ERROR: Video generation returned None")
except Exception as e:
    print(f"ERROR: Video generation failed - {str(e)}")
