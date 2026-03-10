import os
import sys
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration

prompt = """Premium healthcare promotional video. CRITICAL: The ending must be VERY SLOW and SMOOTH with LARGE READABLE TEXT.

SCENE 1 (0-2s): Dark blue background. Healthcare icons float gently - stethoscope, herbs, medical charts, heart monitor. Soft, calm movement.

SCENE 2 (2-4s): Golden warm light appears center. Icons flow gracefully toward it becoming orange and teal light streams.

SCENE 3 (4-6s): Light streams form a smartphone showing HealthTrack Pro app. Modern doctor on left, Ayurvedic healer on right, both connected through the phone.

SCENE 4 (6-7s): App dashboard view - health metrics, lab results, wellness scores displayed cleanly.

SCENE 5 (7-8s): VERY SLOW fade transition begins. Globe with connection points and happy families using phones fades out SLOWLY.

SCENE 6 (8-12s): THIS IS THE MOST IMPORTANT PART. 
- Solid warm orange gradient background (#E55A00)
- VERY LARGE white text fades in SLOWLY over 1 second
- Text displays: "Visit us at infuse-ai.in"
- Below: "for more information"
- Below that: App Store and Play Store download badges
- At bottom: "Create your account at infuse.net.in"
- HealthTrack Pro logo at top center
- ALL TEXT stays perfectly still and readable for FULL 3 SECONDS
- Then VERY SLOW gentle fade to black over 1 second

ENDING REQUIREMENTS: The final 4 seconds MUST show clear, still, readable white text on orange background. Text must say "Visit us at infuse-ai.in for more information" in large font. NO movement, NO animation of text - just static readable text. SMOOTH SLOW fade to black at the very end.

Style: Cinematic, professional healthcare. Orange #E55A00, white text, smooth 24fps. Elegant and calm."""

print("=" * 60)
print("Generating video with SLOW SMOOTH ENDING...")
print("Focus: Large static text 'Visit us at infuse-ai.in'")
print("Ending will hold text for 3+ seconds before slow fade")
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
