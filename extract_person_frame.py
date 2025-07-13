"""
extract_person_frame.py
Clean implementation: Video → Best Single Person Frame

Usage: python extract_person_frame.py
"""

import os
import subprocess
import re
import time
from pathlib import Path
import google.generativeai as genai


class PersonFrameExtractor:
    def __init__(self, api_key):
        """Initialize with Gemini API key"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        # Create output directory
        self.output_dir = Path("output/frames")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_best_person_frame(self, video_path):
        """
        Main function: Video → Best Single Person Frame
        """
        print("🎬 Person Frame Extractor")
        print("=" * 40)
        print(f"📁 Video: {Path(video_path).name}")

        # Step 1: Upload and analyze video
        print("\n📤 Uploading video...")
        video_file = self._upload_and_wait(video_path)

        # Step 2: Find best single person timestamp
        print("🔍 Finding best single person frame...")
        timestamp = self._find_best_person_timestamp(video_file)

        # Step 3: Extract frame using FFmpeg
        print(f"✂️ Extracting frame at {timestamp}s...")
        frame_path = self._extract_frame(video_path, timestamp)

        print(f"\n✅ SUCCESS!")
        print(f"📸 Person frame: {frame_path}")
        print("🔄 Ready for Veo 3!")

        return frame_path

    def _upload_and_wait(self, video_path):
        """Upload video file to Gemini and wait for it to be ready"""
        try:
            print(f"  📤 Uploading {Path(video_path).name}...")
            video_file = genai.upload_file(video_path)
            print(f"  ✅ Upload complete: {video_file.name}")

            # Wait for file to become ACTIVE (with timeout)
            print("  ⏳ Waiting for file to be processed...")
            max_wait_time = 60  # Maximum 60 seconds
            wait_time = 0

            while video_file.state.name == "PROCESSING":
                if wait_time >= max_wait_time:
                    raise Exception(
                        f"Timeout: File processing took longer than {max_wait_time} seconds")

                print(f"    🔄 Still processing... ({wait_time}s)")
                time.sleep(2)
                wait_time += 2
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "ACTIVE":
                print(f"  ✅ File is ready for analysis! (took {wait_time}s)")
                return video_file
            elif video_file.state.name == "FAILED":
                raise Exception(
                    "File processing failed - file may be corrupted or unsupported format")
            else:
                raise Exception(
                    f"Unexpected file state: {video_file.state.name}")

        except Exception as e:
            print(f"  ❌ Upload/processing failed: {e}")
            raise

    def _find_best_person_timestamp(self, video_file):
        """Find timestamp with exactly one person, clear face"""

        prompt = """
        Find the best timestamp where EXACTLY ONE PERSON is clearly visible.
        
        REQUIREMENTS:
        - EXACTLY ONE PERSON in frame (count = 1)
        - Face clearly visible and well-lit
        - No other people anywhere in frame
        - Sharp focus, no blur
        
        If no single-person frames exist:
        BEST_TIMESTAMP: NONE
        
        Otherwise:
        BEST_TIMESTAMP: [seconds]
        REASON: [why this frame is best]
        PEOPLE_COUNT: 1
        """

        response = self.model.generate_content([video_file, prompt])

        # Parse response
        timestamp = self._parse_timestamp(response.text)
        people_count = self._parse_people_count(response.text)
        reason = self._parse_reason(response.text)

        # Validate
        if timestamp == "NONE" or people_count != 1:
            raise Exception("No suitable single-person frames found")

        print(f"  ✅ Found at {timestamp}s: {reason[:50]}...")
        return timestamp

    def _extract_frame(self, video_path, timestamp):
        """Extract frame using FFmpeg"""
        video_name = Path(video_path).stem
        output_file = self.output_dir / \
            f"{video_name}_person_{timestamp:.1f}s.jpg"

        cmd = [
            'ffmpeg', '-i', video_path, '-ss', str(timestamp),
            '-frames:v', '1', '-q:v', '2', '-y', str(output_file)
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0 and output_file.exists():
            print(f"  ✅ Saved: {output_file.name}")
            return str(output_file)
        else:
            raise Exception(f"FFmpeg failed: {result.stderr}")

    def _parse_timestamp(self, text):
        """Extract timestamp from response"""
        if "BEST_TIMESTAMP: NONE" in text:
            return "NONE"
        match = re.search(r'BEST_TIMESTAMP:\s*(\d+\.?\d*)', text)
        return float(match.group(1)) if match else "NONE"

    def _parse_people_count(self, text):
        """Extract people count from response"""
        match = re.search(r'PEOPLE_COUNT:\s*(\d+)', text)
        return int(match.group(1)) if match else 0

    def _parse_reason(self, text):
        """Extract reason from response"""
        match = re.search(r'REASON:\s*(.+)', text)
        return match.group(1).strip() if match else "No reason provided"


def main():
    """Extract person frame from test video"""
    print("🚀 Person Frame Extraction")
    print("=" * 50)

    # Get API key
    API_KEY = os.getenv('GEMINI_API_KEY')
    if not API_KEY:
        print("❌ Please set GEMINI_API_KEY environment variable")
        print("   export GEMINI_API_KEY='your-api-key-here'")
        return

    # Use specific video - FIXED: removed the loop bug
    test_video = "test_videos/IMG_0889.mp4"

    if not os.path.exists(test_video):
        print(f"❌ Test video not found: {test_video}")
        print("   Please make sure the video file exists")
        return

    try:
        # Extract person frame
        extractor = PersonFrameExtractor(API_KEY)
        frame_path = extractor.extract_best_person_frame(test_video)

        print(f"\n🎉 EXTRACTION COMPLETE!")
        print(f"📸 Frame saved: {frame_path}")
        print("🔄 Ready for Veo 3!")

    except Exception as e:
        print(f"\n❌ EXTRACTION FAILED: {e}")


if __name__ == "__main__":
    main()
