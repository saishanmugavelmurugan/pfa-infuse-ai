import os
import sys
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration

prompt = """Professional healthcare app promotional video with smooth transitions:

Opening: Blue gradient background with floating healthcare symbols - stethoscope, herbs, wellness icons drifting peacefully.

Middle: Symbols converge into a glowing smartphone displaying a health tracking app. Show split view of modern and traditional medicine working together through the app interface.

Closing sequence (most important): 
- Warm orange gradient background appears with smooth transition
- Large white text slowly fades in center: "Visit infuse-ai.in"
- Below it: "Download on App Store and Play Store" 
- Text remains completely still and readable for several seconds
- Very gentle slow fade to solid orange, then to black

Style: Premium, cinematic, healthcare marketing. Warm orange and blue color palette. All transitions smooth and professional. Final text must be large, clear, and static."""

print("=" * 60)
print("Generating video with clean ending text...")
print("=" * 60)

try:
    video_gen = OpenAIVideoGeneration(api_key=os.environ['EMERGENT_LLM_KEY'])
    
    video_bytes = video_gen.text_to_video(
        prompt=prompt,
        model="sora-2",
        size="1280x720",
        duration=12,
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
