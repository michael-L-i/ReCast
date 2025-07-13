"""
simple_prompt_generator.py
Simplified: Video → Best Raw Prompt → Anime + Space Versions

Usage: python simple_prompt_generator.py
"""

import os
import time
import json
import re
from pathlib import Path
import google.generativeai as genai
from datetime import datetime


class SimplePromptGenerator:
    def __init__(self, api_key):
        """Initialize with Gemini API key"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        # Create output directory
        self.output_dir = Path("output/prompts")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_prompts(self, video_path):
        """
        Main function: Video → Raw Prompt → Styled Versions
        """
        print("🎬 Simple Prompt Generator")
        print("=" * 40)
        print(f"📁 Video: {Path(video_path).name}")

        # Step 1: Upload video
        print("\n📤 Uploading video...")
        video_file = self._upload_and_wait(video_path)

        # Step 2: Generate raw prompt candidates
        print("🎯 Generating raw prompt candidates...")
        raw_candidates = self._generate_raw_prompts(video_file)

        # Step 3: Select best raw prompt
        print("📊 Selecting best raw prompt...")
        best_raw_prompt = self._select_best_raw_prompt(
            video_file, raw_candidates)

        # Step 4: Generate styled versions
        print("🎨 Creating styled versions...")
        anime_prompt = self._create_anime_version(best_raw_prompt)
        space_prompt = self._create_space_version(best_raw_prompt)

        # Step 5: Save and display results
        print("💾 Saving results...")
        self._save_results(video_path, best_raw_prompt,
                           anime_prompt, space_prompt)

        # Display final results
        print(f"\n🎉 PROMPT GENERATION COMPLETE!")
        print("=" * 60)
        print(f"📝 FINAL RAW PROMPT:")
        print(f"   {best_raw_prompt}")
        print()
        print(f"🎌 FINAL ANIME PROMPT:")
        print(f"   {anime_prompt}")
        print()
        print(f"🚀 FINAL SPACE PROMPT:")
        print(f"   {space_prompt}")
        print("=" * 60)

        return {
            'raw_prompt': best_raw_prompt,
            'anime_prompt': anime_prompt,
            'space_prompt': space_prompt
        }

    def _upload_and_wait(self, video_path):
        """Upload video file to Gemini and wait for it to be ready"""
        try:
            print(f"  📤 Uploading {Path(video_path).name}...")
            video_file = genai.upload_file(video_path)
            print(f"  ✅ Upload complete: {video_file.name}")

            # Wait for file to become ACTIVE
            print("  ⏳ Waiting for processing...")
            max_wait_time = 60
            wait_time = 0

            while video_file.state.name == "PROCESSING":
                if wait_time >= max_wait_time:
                    raise Exception(
                        f"Timeout: Processing took longer than {max_wait_time} seconds")

                print(f"    🔄 Still processing... ({wait_time}s)")
                time.sleep(2)
                wait_time += 2
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "ACTIVE":
                print(f"  ✅ File ready! (took {wait_time}s)")
                return video_file
            else:
                raise Exception(f"Processing failed: {video_file.state.name}")

        except Exception as e:
            print(f"  ❌ Upload failed: {e}")
            raise

    def _generate_raw_prompts(self, video_file):
        """Generate simple raw prompt candidates"""

        candidates = []

        # Strategy 1: Action-focused
        print("  🎯 Action-focused prompt...")
        action_prompt = """
        Watch this video and describe what the person is doing.
        Focus only on actions and movements. Keep it simple and clear.
        Give me just the description, nothing else.
        """

        response1 = self.model.generate_content([video_file, action_prompt])
        action_result = self._parse_raw_prompt(response1.text)
        candidates.append(action_result)
        print(f"    ✅ {action_result[:50]}...")
        # DEBUG: Show what Gemini actually returned (first response only)
        if action_result == "Failed to generate prompt":
            print(f"    🔍 DEBUG: Gemini returned: {response1.text[:100]}...")

        # Strategy 2: Complete description
        print("  🎯 Complete description prompt...")
        complete_prompt = """
        Watch this video and describe what happens from start to finish.
        Include the person's actions and the environment. Keep it natural.
        Give me just the description, nothing else.
        """

        response2 = self.model.generate_content([video_file, complete_prompt])
        complete_result = self._parse_raw_prompt(response2.text)
        candidates.append(complete_result)
        print(f"    ✅ {complete_result[:50]}...")

        # Strategy 3: Simple and clear
        print("  🎯 Simple description prompt...")
        simple_prompt = """
        Describe this video in one clear sentence. What is the main thing happening?
        """

        response3 = self.model.generate_content([video_file, simple_prompt])
        simple_result = self._parse_raw_prompt(response3.text)
        candidates.append(simple_result)
        print(f"    ✅ {simple_result[:50]}...")

        print(f"  ✅ Generated {len(candidates)} raw candidates")
        return candidates

    def _select_best_raw_prompt(self, video_file, candidates):
        """Select the most accurate raw prompt"""

        candidates_text = ""
        for i, candidate in enumerate(candidates, 1):
            candidates_text += f"\nCandidate {i}: {candidate}\n"

        selection_prompt = f"""
        Watch this video and choose which description best matches what actually happens.
        
        CANDIDATES:{candidates_text}
        
        Which candidate is most accurate? Just tell me the number (1, 2, or 3) and why.
        """

        try:
            response = self.model.generate_content(
                [video_file, selection_prompt])

            # Parse response
            best_num = self._parse_best_candidate(response.text)
            reason = self._parse_reason(response.text)

            best_prompt = candidates[best_num - 1]

            print(f"  🏆 Selected candidate {best_num}")
            print(f"  💡 Reason: {reason[:60]}...")

            return best_prompt

        except Exception as e:
            print(f"  ❌ Selection failed: {e}")
            # Fallback: use first candidate
            return candidates[0]

    def _create_anime_version(self, raw_prompt):
        """Transform raw prompt to anime style"""

        anime_prompt = f"""
        Transform this description into anime style:
        
        Original: {raw_prompt}
        
        Make it anime style by adding:
        - Anime visual elements (soft lighting, detailed animation, ethereal effects)
        - Anime-appropriate environments (magical, beautiful, dreamy settings)
        - Keep the same actions but with anime flair
        
        Just give me the anime version description.
        """

        try:
            response = self.model.generate_content(anime_prompt)
            anime_result = self._parse_styled_prompt(response.text, "anime")
            print(f"  ✅ Anime version created")
            return anime_result
        except Exception as e:
            print(f"  ❌ Anime generation failed: {e}")
            return f"{raw_prompt}, anime style with soft lighting and magical atmosphere"

    def _create_space_version(self, raw_prompt):
        """Transform raw prompt to space/sci-fi style"""

        space_prompt = f"""
        Transform this description into space/sci-fi style:
        
        Original: {raw_prompt}
        
        Make it space style by adding:
        - Sci-fi visual elements (metallic surfaces, cosmic lighting, advanced technology)
        - Space environments (space station, alien planet, futuristic setting)
        - Keep the same actions but in a space context
        
        Just give me the space version description.
        """

        try:
            response = self.model.generate_content(space_prompt)
            space_result = self._parse_styled_prompt(response.text, "space")
            print(f"  ✅ Space version created")
            return space_result
        except Exception as e:
            print(f"  ❌ Space generation failed: {e}")
            return f"{raw_prompt}, sci-fi style with metallic surfaces and cosmic lighting"

    def _save_results(self, video_path, raw_prompt, anime_prompt, space_prompt):
        """Save all results to JSON file"""

        video_name = Path(video_path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / \
            f"{video_name}_simple_prompts_{timestamp}.json"

        results = {
            'metadata': {
                'video_path': str(video_path),
                'video_name': video_name,
                'timestamp': datetime.now().isoformat()
            },
            'final_prompts': {
                'raw_prompt': raw_prompt,
                'anime_prompt': anime_prompt,
                'space_prompt': space_prompt
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"  💾 Saved: {output_file.name}")
        return output_file.name

    def _parse_raw_prompt(self, text):
        """Extract raw prompt from response - flexible parsing"""
        # Remove the strict format requirement and just use the response
        if text and text.strip():
            # Clean up the response
            cleaned = text.strip()
            # Remove any common prefixes if they exist
            if cleaned.startswith("RAW_PROMPT:"):
                cleaned = cleaned.replace("RAW_PROMPT:", "").strip()
            return cleaned
        return "Failed to generate prompt"

    def _parse_styled_prompt(self, text, style_type):
        """Extract styled prompt from response - flexible parsing"""
        if text and text.strip():
            cleaned = text.strip()
            # Remove any common prefixes if they exist
            prefixes_to_remove = [
                f"{style_type.upper()}_PROMPT:",
                "ANIME_PROMPT:",
                "SPACE_PROMPT:",
                f"{style_type} version:",
                f"{style_type} style:"
            ]

            for prefix in prefixes_to_remove:
                if cleaned.startswith(prefix):
                    cleaned = cleaned.replace(prefix, "").strip()
                    break

            return cleaned
        return f"Failed to generate {style_type} prompt"

    def _parse_anime_prompt(self, text):
        """Extract anime prompt from response"""
        return self._parse_styled_prompt(text, "anime")

    def _parse_space_prompt(self, text):
        """Extract space prompt from response"""
        return self._parse_styled_prompt(text, "space")

    def _parse_best_candidate(self, text):
        """Extract best candidate number - flexible parsing"""
        # Look for number patterns
        numbers = re.findall(r'\b[123]\b', text)
        if numbers:
            return int(numbers[0])

        # Look for specific patterns
        if "candidate 1" in text.lower() or "first" in text.lower():
            return 1
        elif "candidate 2" in text.lower() or "second" in text.lower():
            return 2
        elif "candidate 3" in text.lower() or "third" in text.lower():
            return 3

        return 1  # Default to first candidate

    def _parse_reason(self, text):
        """Extract reason from response - flexible parsing"""
        # Try to find structured reason first
        reason_match = re.search(r'REASON:\s*(.+)', text, re.DOTALL)
        if reason_match:
            return reason_match.group(1).strip()

        # Otherwise just use the whole response as reason
        if text and text.strip():
            return text.strip()

        return "No reason provided"


def main():
    """Generate simple prompts from test video"""
    print("🚀 Simple Prompt Generation")
    print("=" * 50)

    # Get API key
    API_KEY = os.getenv('GEMINI_API_KEY')
    if not API_KEY:
        print("❌ Please set GEMINI_API_KEY environment variable")
        print("   export GEMINI_API_KEY='your-api-key-here'")
        return

    # Use specific video
    test_video = "test_videos/IMG_0889.mp4"

    if not os.path.exists(test_video):
        print(f"❌ Test video not found: {test_video}")
        print("   Please make sure the video file exists")
        return

    try:
        # Generate prompts
        generator = SimplePromptGenerator(API_KEY)
        results = generator.generate_prompts(test_video)

        print(f"\n✅ ALL PROMPTS READY FOR VEO 3!")

    except Exception as e:
        print(f"\n❌ GENERATION FAILED: {e}")


if __name__ == "__main__":
    main()
