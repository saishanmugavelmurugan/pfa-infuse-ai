import os
import sys
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration

prompt = """Smooth animated healthcare marketing video:

Scene 1: Multiple scattered health documents (lab reports, prescriptions, fitness data, medical records) floating chaotically in space against a dark blue background.

Scene 2: The documents start flowing together, merging into a glowing smartphone showing the HealthTrack Pro app interface with unified health dashboard.

Scene 3: From the phone, holographic health insights emerge - a heart rate graph, nutrition chart, and predictive health score rising upward.

Scene 4: Zoom out to show a happy Indian family (parents and child) smiling at the phone, surrounded by a warm orange glow representing health and wellness.

Style: Modern, clean, premium healthcare aesthetic with orange (#E55A00) and teal accent colors. Smooth transitions, professional motion graphics."""

print("Starting video generation with Sora 2...")
print("This may take 3-5 minutes...")

video_gen = OpenAIVideoGeneration(api_key=os.environ['EMERGENT_LLM_KEY'])

video_bytes = video_gen.text_to_video(
    prompt=prompt,
    model="sora-2",
    size="1280x720",
    duration=8,
    max_wait_time=600
)

if video_bytes:
    output_path = "/app/frontend/public/downloads/HealthTrackPro_Promo_Video.mp4"
    video_gen.save_video(video_bytes, output_path)
    print(f"✅ Video saved to: {output_path}")
else:
    print("❌ Video generation failed")
