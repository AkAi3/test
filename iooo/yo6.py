import cv2
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import make_chunks
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

# Initialize the recognizer
recognizer = sr.Recognizer()

# Input and output file paths
input_video_path = r'C:\Users\Shridhar\Desktop\iooo\input.mp4'
output_video_path = r'C:\Users\Shridhar\Desktop\iooo\final_output.mp4'
output_audio_path = r'C:\Users\Shridhar\Desktop\iooo\output_audio.wav'

# List of inappropriate words to censor
inappropriate_words = ['badword1', 'badword2', 'badword3']  # Add the words you want to censor

# Function to censor inappropriate words
def censor_text(text):
    words = text.split()
    censored_words = [
        '*' * len(word) if word.lower() in inappropriate_words else word
        for word in words
    ]
    return ' '.join(censored_words)

# Extract audio from the video
def extract_audio(video_path):
    video = VideoFileClip(video_path)
    audio_path = r"C:\Users\Shridhar\Desktop\iooo\temp_audio.wav"
    video.audio.write_audiofile(audio_path, codec='pcm_s16le')
    return audio_path

# Process audio to generate subtitles and mute inappropriate words
def process_audio(audio_path):
    audio = AudioSegment.from_file(audio_path)
    chunks = make_chunks(audio, 1000)  # Chunk audio into 1-second segments
    final_audio = AudioSegment.empty()
    subtitles = []

    for i, chunk in enumerate(chunks):
        try:
            raw_data = chunk.raw_data
            audio_data = sr.AudioData(raw_data, sample_rate=44100, sample_width=2)
            text = recognizer.recognize_google(audio_data)
            censored_text = censor_text(text)

            if any(word in text.lower() for word in inappropriate_words):
                chunk = AudioSegment.silent(duration=len(chunk))  # Mute the audio
                subtitles.append((censored_text, True, i * 1000))  # Store subtitle, censorship flag, and timestamp
            else:
                subtitles.append((censored_text, False, i * 1000))  # Store subtitle and timestamp

            final_audio += chunk

        except sr.UnknownValueError:
            subtitles.append(("Could not understand audio", False, i * 1000))
            final_audio += chunk
        except sr.RequestError as e:
            subtitles.append((f"Could not request results; {e}", False, i * 1000))
            final_audio += chunk

    final_audio.export(output_audio_path, format="wav")
    return subtitles

# Overlay subtitles on video
def overlay_subtitles(video_path, subtitles):
    cap = cv2.VideoCapture(video_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = cv2.VideoWriter(r'C:\Users\Shridhar\Desktop\iooo\output_with_subtitles.avi', cv2.VideoWriter_fourcc(*'MJPG'), fps, (frame_width, frame_height))

    font = cv2.FONT_HERSHEY_SIMPLEX
    frame_duration = 1000 / fps  # Duration of each frame in milliseconds

    frame_count = 0
    subtitle_index = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Calculate current timestamp
        timestamp = frame_count * frame_duration

        if subtitle_index < len(subtitles):
            subtitle, is_censored, subtitle_time = subtitles[subtitle_index]
            if timestamp >= subtitle_time:
                if is_censored:
                    # Display a black rectangle to censor the video
                    frame = cv2.rectangle(frame, (0, frame_height // 2 - 50), (frame_width, frame_height // 2 + 50), (0, 0, 0), -1)

                # Display subtitle on the frame
                frame = cv2.putText(frame, subtitle, (50, 50), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
                subtitle_index += 1

        out.write(frame)
        frame_count += 1

    cap.release()
    out.release()

# Main function to process video
def process_video(input_video_path):
    audio_path = extract_audio(input_video_path)
    subtitles = process_audio(audio_path)
    overlay_subtitles(input_video_path, subtitles)

    # Combine the video and audio using moviepy
    video_clip = VideoFileClip(r'C:\Users\Shridhar\Desktop\iooo\output_with_subtitles.avi')
    audio_clip = AudioFileClip(output_audio_path)

    final_clip = video_clip.set_audio(audio_clip)
    final_clip.write_videofile(output_video_path, codec="libx264")

    print("Video saved successfully.")

if __name__ == "__main__":
    process_video(input_video_path)
