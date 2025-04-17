from moviepy.editor import VideoFileClip, concatenate_audioclips
from moviepy.audio.fx.all import volumex
import speech_recognition as sr

def extract_audio(video_path, audio_path):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)

def transcribe_audio_with_timestamps(audio_path, target_words):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            words = text.split()
            timestamps = []
            for i, word in enumerate(words):
                if any(target_word.lower() in word.lower() for target_word in target_words):
                    # Calculate timestamp (approximate)
                    timestamp = (i / len(words)) * source.DURATION
                    timestamps.append(timestamp)
            return timestamps
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand the audio")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")

def mute_audio_at_timestamps(video_path, output_path, timestamps, duration=0.8):
    video = VideoFileClip(video_path)
    audio = video.audio

    # Create a list to hold the audio segments
    segments = []
    start = 0

    for timestamp in timestamps:
        segments.append(audio.subclip(start, timestamp))
        silent_audio = audio.subclip(timestamp, timestamp + duration).fx(volumex, 0)
        segments.append(silent_audio)
        start = timestamp + duration
        
        print (timestamps)
        
        
    #for start_time, end_time in timestamps:
     #   segments.append(audio.subclip(start, start_time))
      #  silent_audio = audio.subclip(start_time, end_time).fx(volumex, 0)
       # segments.append(silent_audio)
        #start = end_time

    # Add the remaining part of the audio
    segments.append(audio.subclip(start))

    # Concatenate all segments
    new_audio = concatenate_audioclips(segments)

    # Set the new audio to the video
    new_video = video.set_audio(new_audio)
    new_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

# Example usage
video_path = "C:/Users/revan/OneDrive/Desktop/auto bleeper/input_ruman.mp4"
audio_path = "extracted_audio.wav"
target_words = ["Everyone", "endlessly"]

extract_audio(video_path, audio_path)
timestamps = transcribe_audio_with_timestamps(audio_path, target_words)

if timestamps:
    mute_audio_at_timestamps(video_path, "muted_video.mp4", timestamps)
else:
    print("Target words not found in the audio.")