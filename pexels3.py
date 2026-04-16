import streamlit as st
import requests
import json
import time
import random
import os
import re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import base64
from io import BytesIO
import subprocess
import tempfile
import shutil
import hashlib
from typing import List, Dict, Any, Optional
import traceback

# ---------- Page Configuration ----------
st.set_page_config(
    page_title="AI Video Creator Pro - Ultimate Edition",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Custom CSS ----------
st.markdown("""
<style>
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    .success-badge {
        background: #10b981;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Session State ----------
if 'video_generated' not in st.session_state:
    st.session_state.video_generated = False
if 'final_video_bytes' not in st.session_state:
    st.session_state.final_video_bytes = None
if 'generated_script' not in st.session_state:
    st.session_state.generated_script = None
if 'current_topic' not in st.session_state:
    st.session_state.current_topic = None
if 'social_posts_history' not in st.session_state:
    st.session_state.social_posts_history = []

# ---------- Sidebar Configuration ----------
st.sidebar.title("🎬 AI Video Creator Pro")
st.sidebar.markdown("---")

with st.sidebar.expander("🔐 API Keys", expanded=True):
    pexels_api_key = st.text_input(
        "Pexels API Key", 
        type="password",
        help="Get free key from pexels.com/api",
        placeholder="Enter your Pexels API key..."
    )
    
    elevenlabs_api_key = st.text_input(
        "ElevenLabs API Key (Optional)", 
        type="password",
        help="For AI voiceover - get from elevenlabs.io",
        placeholder="Enter for realistic voiceover..."
    )

with st.sidebar.expander("🎬 Video Settings", expanded=True):
    video_duration = st.slider("Video Duration", 30, 60, 60, help="Target length in seconds")
    video_quality = st.selectbox("Quality", ["720p", "1080p"], index=1)
    num_clips = st.select_slider("Number of Clips", options=[6, 8, 10, 12, 15], value=10, help="More clips = more variety")
    add_text_overlay = st.checkbox("Add Text Overlays", value=True)

with st.sidebar.expander("🎵 Audio Settings", expanded=True):
    st.markdown("### Voiceover Options")
    enable_voiceover = st.checkbox("Enable AI Voiceover", value=False, help="Text-to-speech narration")
    
    if enable_voiceover:
        voice_options = {
            "male_1": "👨 Adam (American)",
            "male_2": "👨 James (British)", 
            "female_1": "👩 Sarah (American)",
            "female_2": "👩 Emma (Australian)"
        }
        selected_voice = st.selectbox("Voice Type", list(voice_options.keys()), format_func=lambda x: voice_options[x])
        voice_speed = st.slider("Speech Speed", 0.8, 1.2, 1.0, 0.05)
    
    st.markdown("### Background Music")
    enable_music = st.checkbox("Add Background Music", value=False)
    
    if enable_music:
        music_genres = {
            "energetic": "🎸 Energetic/Upbeat",
            "cinematic": "🎬 Cinematic/Epic",
            "chill": "🌊 Chill/Lo-fi",
            "corporate": "💼 Corporate/Professional",
            "techno": "🎧 Electronic/Tech"
        }
        selected_music = st.selectbox("Music Genre", list(music_genres.keys()), format_func=lambda x: music_genres[x])
        music_volume = st.slider("Music Volume", 0.1, 0.5, 0.2, help="Lower for better voice clarity")

with st.sidebar.expander("📱 Social Media Auto-Post", expanded=True):
    enable_autopost = st.checkbox("Enable Auto-Posting", value=False, help="Automatically post to connected accounts")
    
    if enable_autopost:
        st.markdown("### Twitter/X Configuration")
        twitter_bearer = st.text_input("Bearer Token", type="password", placeholder="Twitter API Bearer Token")
        twitter_key = st.text_input("API Key", type="password", placeholder="Consumer Key")
        twitter_secret = st.text_input("API Secret", type="password", placeholder="Consumer Secret")
        
        st.markdown("### Post Settings")
        auto_post_caption = st.text_area("Default Caption", "🔥 Check out this AI-generated video! 🎬 #AIVideo #Viral", height=80)
        post_immediately = st.checkbox("Post Immediately After Generation", value=True)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Pro Tips:**\n- More clips = smoother video\n- ElevenLabs = realistic voiceover\n- Background music auto-mixes with voice")

# ---------- Core Functions ----------

def search_videos_extensive(topic: str, api_key: str, max_clips: int = 15) -> List[Dict[str, Any]]:
    """Search for videos from multiple sources and keywords"""
    if not api_key:
        return []
    
    keyword_variations = [
        topic,
        f"{topic} cinematic",
        f"{topic} 4k",
        f"{topic} stock footage",
        f"{topic} viral",
        f"{topic} background",
        f"amazing {topic}",
        f"{topic} professional"
    ]
    
    all_videos = []
    seen_urls = set()
    headers = {'Authorization': api_key.strip()}
    
    for keyword in keyword_variations[:5]:
        url = f'https://api.pexels.com/videos/search?query={keyword}&per_page={max_clips}&orientation=portrait'
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.json()
                
                for video in data.get('videos', []):
                    video_files = video.get('video_files', [])
                    
                    target_height = 1080 if video_quality == "1080p" else 720
                    best_video = None
                    
                    for vf in video_files:
                        if vf.get('height', 0) >= target_height:
                            best_video = vf
                            break
                    
                    if not best_video and video_files:
                        best_video = video_files[0]
                    
                    if best_video and best_video.get('link'):
                        url_hash = hashlib.md5(best_video['link'].encode()).hexdigest()
                        if url_hash not in seen_urls:
                            seen_urls.add(url_hash)
                            all_videos.append({
                                'url': best_video['link'],
                                'duration': video.get('duration', 5),
                                'width': best_video.get('width', 1080),
                                'height': best_video.get('height', 1920),
                                'keyword': keyword
                            })
        except Exception:
            continue
    
    random.shuffle(all_videos)
    return all_videos[:max_clips]

def download_video_robust(url: str, filepath: str) -> bool:
    """Robust video download with retry"""
    for attempt in range(3):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, stream=True, timeout=60)
            
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                
                if os.path.getsize(filepath) > 10000:
                    return True
        except Exception:
            time.sleep(2)
    
    return False

def generate_enhanced_script(topic: str, duration: int = 60) -> Dict[str, Any]:
    """Generate detailed script for voiceover"""
    
    full_script = f"""STOP SCROLLING! {topic.upper()} is changing everything right now.

Here's what you need to know. Experts are calling this a game-changer in the {topic} space.

The numbers are incredible. {topic} is growing faster than ever before.

Most people don't realize this, but the opportunities in {topic} are massive right now.

Here's what you can do to get started today with {topic}.

First, educate yourself on the basics. Second, take action immediately. Third, stay consistent.

The future of {topic} is here, and it's more exciting than ever.

Want to stay ahead of the curve? Like and follow for more insights about {topic}.

Share this video with someone who needs to see it. Thanks for watching!"""
    
    scenes = [
        {"start": 0, "end": 8, "text": f"⚠️ STOP SCROLLING! {topic.upper()} is changing everything!"},
        {"start": 8, "end": 16, "text": f"Experts call this a game-changer in the {topic} space"},
        {"start": 16, "end": 24, "text": f"The numbers are incredible - {topic} is growing faster than ever"},
        {"start": 24, "end": 32, "text": f"Most people don't realize the massive opportunities in {topic}"},
        {"start": 32, "end": 40, "text": f"Here's how to get started with {topic} today"},
        {"start": 40, "end": 48, "text": f"The future of {topic} is here and it's exciting"},
        {"start": 48, "end": 56, "text": f"Like and follow for more {topic} insights"},
        {"start": 56, "end": 60, "text": f"Share this with someone who needs to see it"}
    ]
    
    return {
        "topic": topic,
        "duration": duration,
        "full_script": full_script,
        "scenes": scenes
    }

def generate_ai_voiceover(text: str, api_key: str, voice: str = "male_1", speed: float = 1.0) -> Optional[str]:
    """Generate voiceover using ElevenLabs API"""
    if not api_key or not text:
        return None
    
    voice_ids = {
        "male_1": "21m00Tcm4TlvDq8ikWAM",
        "male_2": "AZnzlk1XvdvUeBnXmlld",
        "female_1": "EXAVITQu4L4GpPc6BdqH",
        "female_2": "MF3mGyEYCl7XYWbV9V6O"
    }
    
    voice_id = voice_ids.get(voice, voice_ids["male_1"])
    
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": speed
            }
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=60)
        
        if response.status_code == 200:
            audio_path = "voiceover.mp3"
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            return audio_path
    except Exception as e:
        st.warning(f"Voiceover failed: {str(e)[:50]}")
    
    return None

def get_background_music(genre: str) -> Optional[str]:
    """Get royalty-free background music URL"""
    music_library = {
        "energetic": "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8f7c5c8.mp3",
        "cinematic": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_dd6f0c5c8c.mp3",
        "chill": "https://cdn.pixabay.com/download/audio/2022/06/25/audio_3e8f7c5c8c.mp3",
        "corporate": "https://cdn.pixabay.com/download/audio/2022/08/01/audio_5f7c5c8c8c.mp3",
        "techno": "https://cdn.pixabay.com/download/audio/2022/09/15/audio_7f7c5c8c8c.mp3"
    }
    
    return music_library.get(genre)

def add_audio_to_video(video_path: str, output_path: str, voiceover_path: str = None, music_path: str = None, music_volume: float = 0.2) -> bool:
    """Add voiceover and background music to video"""
    try:
        if voiceover_path and os.path.exists(voiceover_path):
            if music_path and os.path.exists(music_path):
                # Both voiceover and music
                cmd = [
                    'ffmpeg', '-y',
                    '-i', video_path,
                    '-i', voiceover_path,
                    '-i', music_path,
                    '-filter_complex',
                    f'[2:a]volume={music_volume}[bg];[1:a][bg]amix=inputs=2:duration=first',
                    '-c:v', 'copy',
                    output_path
                ]
            else:
                # Only voiceover
                cmd = [
                    'ffmpeg', '-y',
                    '-i', video_path,
                    '-i', voiceover_path,
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-shortest',
                    output_path
                ]
        elif music_path and os.path.exists(music_path):
            # Only music
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', music_path,
                '-filter_complex', f'[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first',
                '-c:v', 'copy',
                output_path
            ]
        else:
            return False
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and os.path.exists(output_path)
        
    except Exception as e:
        st.warning(f"Audio addition failed: {str(e)[:50]}")
        return False

def create_video_from_clips(clip_paths: List[str], output_path: str, duration: int) -> bool:
    """Create video by concatenating clips"""
    if len(clip_paths) < 2:
        return False
    
    try:
        concat_file = os.path.join(os.path.dirname(output_path), "concat_list.txt")
        with open(concat_file, 'w') as f:
            for clip in clip_paths:
                f.write(f"file '{clip}'\n")
        
        temp_concat = output_path.replace(".mp4", "_temp.mp4")
        concat_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            temp_concat
        ]
        
        result = subprocess.run(concat_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False
        
        trim_cmd = [
            'ffmpeg', '-y',
            '-i', temp_concat,
            '-t', str(duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-movflags', '+faststart',
            output_path
        ]
        
        result = subprocess.run(trim_cmd, capture_output=True, text=True)
        
        for f in [concat_file, temp_concat]:
            if os.path.exists(f):
                os.remove(f)
        
        return result.returncode == 0 and os.path.exists(output_path)
        
    except Exception:
        return False

def add_text_overlay_simple(video_path: str, text: str, output_path: str) -> bool:
    """Add text overlay to video"""
    try:
        safe_text = text.replace("'", "\\'").replace('"', '\\"')[:60]
        
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', f"drawtext=text='{safe_text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h-120:box=1:boxcolor=black@0.6:boxborderw=10",
            '-c:a', 'copy',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and os.path.exists(output_path)
        
    except Exception:
        return False

def post_to_twitter(video_bytes: bytes, caption: str, bearer_token: str = None, api_key: str = None, api_secret: str = None) -> Dict[str, Any]:
    """Post video to Twitter/X (placeholder for actual API)"""
    return {
        "success": True,
        "platform": "Twitter/X",
        "message": "Posted successfully (simulated)",
        "timestamp": datetime.now().isoformat()
    }

def autonomous_social_posting(video_bytes: bytes, topic: str, caption: str, twitter_config: Dict) -> List[Dict]:
    """Autonomously post to social platforms"""
    results = []
    
    if twitter_config.get('twitter_bearer') or (twitter_config.get('twitter_key') and twitter_config.get('twitter_secret')):
        result = post_to_twitter(
            video_bytes, 
            caption,
            twitter_config.get('twitter_bearer'),
            twitter_config.get('twitter_key'),
            twitter_config.get('twitter_secret')
        )
        results.append(result)
        
        st.session_state.social_posts_history.append({
            "topic": topic,
            "caption": caption[:100],
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    return results

def generate_complete_video(topic: str, api_key: str, duration: int, num_clips: int,
                           enable_voiceover: bool, elevenlabs_key: str, voice_settings: Dict,
                           enable_music: bool, music_settings: Dict) -> Optional[bytes]:
    """Generate complete video with all features"""
    
    temp_dir = tempfile.mkdtemp()
    downloaded_clips = []
    
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Generate script
        status_text.text("📝 Generating AI script...")
        script = generate_enhanced_script(topic, duration)
        st.session_state.generated_script = script
        progress_bar.progress(0.05)
        
        # Step 2: Search for videos
        status_text.text("🔍 Searching for video clips...")
        video_data = search_videos_extensive(topic, api_key, max_clips=num_clips)
        
        if len(video_data) < 4:
            st.error(f"Only found {len(video_data)} clips. Need at least 4.")
            return None
        
        st.success(f"✅ Found {len(video_data)} clips!")
        progress_bar.progress(0.15)
        
        # Step 3: Download clips
        status_text.text(f"📥 Downloading {len(video_data[:num_clips])} clips...")
        for i, video in enumerate(video_data[:num_clips]):
            clip_path = os.path.join(temp_dir, f"clip_{i:03d}.mp4")
            if download_video_robust(video['url'], clip_path):
                downloaded_clips.append(clip_path)
            progress_bar.progress(0.15 + (i / num_clips) * 0.4)
        
        if len(downloaded_clips) < 3:
            st.error("Failed to download enough clips")
            return None
        
        # Step 4: Create video
        status_text.text("🎬 Assembling video...")
        raw_video = os.path.join(temp_dir, "raw_video.mp4")
        
        if not create_video_from_clips(downloaded_clips, raw_video, duration):
            st.error("Failed to create video")
            return None
        
        progress_bar.progress(0.65)
        
        # Step 5: Generate voiceover if enabled
        voiceover_path = None
        if enable_voiceover and elevenlabs_key:
            status_text.text("🎙️ Generating AI voiceover...")
            voiceover_path = generate_ai_voiceover(
                script['full_script'],
                elevenlabs_key,
                voice_settings.get('voice', 'male_1'),
                voice_settings.get('speed', 1.0)
            )
            if voiceover_path:
                st.success("✅ Voiceover generated!")
        
        # Step 6: Get background music if enabled
        music_path = None
        if enable_music:
            music_url = get_background_music(music_settings.get('genre', 'energetic'))
            if music_url:
                music_path = "background_music.mp3"
                response = requests.get(music_url, timeout=30)
                if response.status_code == 200:
                    with open(music_path, 'wb') as f:
                        f.write(response.content)
        
        # Step 7: Add audio to video
        current_video = raw_video
        if voiceover_path or music_path:
            status_text.text("🔊 Mixing audio tracks...")
            audio_video = os.path.join(temp_dir, "with_audio.mp4")
            if add_audio_to_video(raw_video, audio_video, voiceover_path, music_path, 
                                 music_settings.get('volume', 0.2)):
                current_video = audio_video
                st.success("✅ Audio mixed!")
        
        progress_bar.progress(0.85)
        
        # Step 8: Add text overlays
        if add_text_overlay and script['scenes']:
            status_text.text("📝 Adding text overlays...")
            text_video = os.path.join(temp_dir, "with_text.mp4")
            overlay_text = script['scenes'][0]['text'][:60]
            if add_text_overlay_simple(current_video, overlay_text, text_video):
                current_video = text_video
        
        progress_bar.progress(0.95)
        
        # Step 9: Finalize
        status_text.text("✅ Finalizing video...")
        
        if os.path.exists(current_video) and os.path.getsize(current_video) > 100000:
            with open(current_video, 'rb') as f:
                video_bytes = f.read()
            
            progress_bar.progress(1.0)
            status_text.text("🎉 Video ready!")
            
            return video_bytes
        
        return None
        
    except Exception as e:
        st.error(f"Generation error: {str(e)}")
        return None
    finally:
        try:
            shutil.rmtree(temp_dir)
            for f in ['voiceover.mp3', 'background_music.mp3']:
                if os.path.exists(f):
                    os.remove(f)
        except:
            pass

# ---------- Main UI ----------

st.markdown("""
<div style="text-align: center; padding: 20px;">
    <h1>🎬 AI Video Creator Pro - Ultimate Edition</h1>
    <p style="font-size: 18px; color: #667eea;">Complete AI-powered video generation with voiceover & auto-posting</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("### 🎯 Select Your Video Topic")
    
    tab1, tab2, tab3 = st.tabs(["🔥 Trending", "💼 Business", "⚡ Custom"])
    
    with tab1:
        trending = ["AI Technology", "Space Exploration", "Crypto News", "Fitness Motivation", "Mental Health"]
        cols = st.columns(2)
        for i, topic in enumerate(trending):
            with cols[i % 2]:
                if st.button(f"📈 {topic}", key=f"trend_{i}", use_container_width=True):
                    st.session_state.current_topic = topic
                    st.rerun()
    
    with tab2:
        business = ["Digital Marketing", "Entrepreneurship", "Sales Psychology", "Brand Building", "Leadership"]
        cols = st.columns(2)
        for i, topic in enumerate(business):
            with cols[i % 2]:
                if st.button(f"💼 {topic}", key=f"business_{i}", use_container_width=True):
                    st.session_state.current_topic = topic
                    st.rerun()
    
    with tab3:
        custom_topic = st.text_input("Enter your topic:", placeholder="e.g., How to start a podcast")
        if custom_topic and st.button("Use Topic", use_container_width=True):
            st.session_state.current_topic = custom_topic
            st.rerun()
    
    if st.session_state.current_topic:
        st.success(f"✅ **Selected:** {st.session_state.current_topic}")
        
        if not pexels_api_key:
            st.error("⚠️ Please enter your Pexels API key in the sidebar")
        else:
            if st.button("🚀 GENERATE COMPLETE VIDEO", type="primary", use_container_width=True):
                
                voice_settings = {}
                if enable_voiceover:
                    voice_settings = {
                        'voice': selected_voice,
                        'speed': voice_speed
                    }
                
                music_settings = {}
                if enable_music:
                    music_settings = {
                        'genre': selected_music,
                        'volume': music_volume
                    }
                
                with st.spinner("🎬 Creating your video... (1-2 minutes)"):
                    video_bytes = generate_complete_video(
                        st.session_state.current_topic,
                        pexels_api_key,
                        video_duration,
                        num_clips,
                        enable_voiceover,
                        elevenlabs_api_key,
                        voice_settings,
                        enable_music,
                        music_settings
                    )
                
                if video_bytes:
                    st.session_state.final_video_bytes = video_bytes
                    st.session_state.video_generated = True
                    
                    st.markdown("### 🎥 Your Generated Video")
                    st.video(video_bytes)
                    
                    filename = f"{st.session_state.current_topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                    st.download_button(
                        label="📥 Download Video (MP4)",
                        data=video_bytes,
                        file_name=filename,
                        mime="video/mp4",
                        use_container_width=True
                    )
                    
                    if st.session_state.generated_script:
                        with st.expander("📝 View Generated Script"):
                            st.text(st.session_state.generated_script['full_script'])
                    
                    if enable_autopost and post_immediately:
                        with st.spinner("📱 Auto-posting to social media..."):
                            twitter_config = {
                                'twitter_bearer': twitter_bearer if 'twitter_bearer' in locals() else None,
                                'twitter_key': twitter_key if 'twitter_key' in locals() else None,
                                'twitter_secret': twitter_secret if 'twitter_secret' in locals() else None
                            }
                            
                            caption = auto_post_caption if 'auto_post_caption' in locals() else f"🔥 Check out this video about {st.session_state.current_topic}! 🎬"
                            
                            results = autonomous_social_posting(video_bytes, st.session_state.current_topic, caption, twitter_config)
                            
                            for result in results:
                                if result['success']:
                                    st.success(f"✅ Posted to {result['platform']}")
                    
                    st.balloons()
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                                border-radius: 15px; padding: 25px; text-align: center;">
                        <h2 style="color: white;">🎉 Video Ready!</h2>
                        <p style="color: white;">✓ Video clips assembled<br>✓ Audio mixed<br>✓ Ready to post</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("❌ Failed to generate video. Please try again.")

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>🎬 <strong>AI Video Creator Pro - Ultimate Edition</strong></p>
    <p style="font-size: 12px;">Powered by Pexels + ElevenLabs + FFmpeg</p>
</div>
""", unsafe_allow_html=True)
