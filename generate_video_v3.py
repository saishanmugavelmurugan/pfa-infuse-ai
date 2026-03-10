import os
import sys
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration

prompt = """Cinematic healthcare promotional video with SMOOTH professional animation and CLEAR TEXT overlays:

SCENE 1 (0-2s): Dark blue gradient background. Floating healthcare elements appear smoothly - stethoscope, Ayurvedic herbs, medical charts, heart monitor, yoga pose silhouette. Elements drift gently representing fragmented healthcare.

SCENE 2 (2-4s): Golden light emerges from center. All elements gracefully flow toward it, transforming into glowing orange and teal data streams. Smooth particle effects.

SCENE 3 (4-6s): Streams elegantly merge into a sleek smartphone displaying HealthTrack Pro app. Split view: modern doctor (left) and Ayurvedic practitioner (right), connected through the screen. AI patterns pulse softly in background.

SCENE 4 (6-8s): Smooth zoom into phone showing unified dashboard - lab results, Ayurvedic recommendations, health score rising. Clean, modern interface animation.

SCENE 5 (8-10s): Gentle pull back revealing global map with glowing connection points. Happy diverse families using the app on their phones. Warm, inviting atmosphere.

SCENE 6 (10-12s): SMOOTH FADE to clean orange gradient background (#E55A00). Center screen displays in LARGE CLEAR WHITE TEXT:

"Visit us at infuse-ai.in"

Below that, App Store and Google Play Store icons side by side.

Below icons: "Create your account at infuse.net.in"

HealthTrack Pro logo at top. Text remains on screen for full 2 seconds. Gentle fade to black at very end.

CRITICAL: Final frame MUST show clear readable text "Visit us at infuse-ai.in" and "infuse.net.in" with smooth fade out ending.

Style: Premium healthcare marketing. Colors: Deep blue, orange #E55A00, teal, white text. 24fps smooth animation. Professional, warm, approachable. All transitions must be SMOOTH with no abrupt cuts."""

print("=" * 60)
print("Generating IMPROVED promotional video with Sora 2...")
print("Focus: Smooth ending + Clear 'Visit infuse-ai.in' text")
print("This may take 5-8 minutes...")
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
