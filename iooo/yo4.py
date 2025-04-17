import cv2
import pyaudio
import speech_recognition as sr
import numpy as np
import threading
from pydub import AudioSegment
from pydub.utils import make_chunks
from moviepy.editor import VideoFileClip, AudioFileClip

# Initialize the recognizer
recognizer = sr.Recognizer()

# Initialize video capture
cap = cv2.VideoCapture(0)

# Check if the video capture is initialized successfully
if not cap.isOpened():
    print("Error: Could not open video capture.")
    exit()

# Get the default video frame width and height
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Define the codec and create VideoWriter object to save the video
out = cv2.VideoWriter('output.avi', cv2.VideoWriter_fourcc(*'MJPG'), 10, (frame_width, frame_height))

# Check if the VideoWriter is initialized successfully
if not out.isOpened():
    print("Error: Could not open VideoWriter.")
    cap.release()
    exit()

# Initialize PyAudio
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

# Variable to store the subtitles and audio segments
subtitle = ""
audio_segments = []

# List of inappropriate words to censor
inappropriate_words = ['dog', 'fuck', 'why']  # Add the words you want to censor

# Function to censor inappropriate words
def censor_text(text):
    words = text.split()
    censored_words = [
        '*' * len(word) if word.lower() in inappropriate_words else word
        for word in words
    ]
    return ' '.join(censored_words)

# Function to capture audio and recognize speech
def capture_audio():
    global subtitle, audio_segments
    while True:
        with sr.Microphone() as source:
            try:
                audio_data = recognizer.listen(source, timeout=3)
                text = recognizer.recognize_google(audio_data)
                subtitle = censor_text(text)
                
                # Convert audio_data to AudioSegment
                raw_data = audio_data.get_raw_data()
                temp_audio = AudioSegment(
                    data=raw_data, 
                    sample_width=2, 
                    frame_rate=44100, 
                    channels=1
                )
                
                # Check for inappropriate words and mute if found
                if any(word in text.lower() for word in inappropriate_words):
                    muted_segment = AudioSegment.silent(duration=len(temp_audio))
                    audio_segments.append(muted_segment)
                else:
                    audio_segments.append(temp_audio)
            except sr.UnknownValueError:
                subtitle = "Could not understand audio"
            except sr.RequestError as e:
                subtitle = f"Could not request results; {e}"
            except sr.WaitTimeoutError:
                subtitle = "Listening timeout"

# Start the audio capture thread
audio_thread = threading.Thread(target=capture_audio)
audio_thread.daemon = True
audio_thread.start()

# Main loop to capture video, overlay subtitles, and save the video
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame.")
        break

    # Display subtitle on the frame
    font = cv2.FONT_HERSHEY_SIMPLEX
    y0, dy = 50, 30
    for i, line in enumerate(subtitle.split('\n')):
        y = y0 + i * dy
        cv2.putText(frame, line, (50, y), font, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # Write the frame into the file 'output.avi'
    out.write(frame)

    # Display the resulting frame
    cv2.imshow('Live Video with Subtitles', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything is done, release the capture and close windows
cap.release()
out.release()
cv2.destroyAllWindows()
stream.stop_stream()
stream.close()
p.terminate()

# Combine the audio segments into one
final_audio = sum(audio_segments)

# Save the final audio segment
final_audio.export("output_audio.wav", format="wav")

# Combine the video and audio using moviepy
video_clip = VideoFileClip("output.avi")
audio_clip = AudioFileClip("output_audio.wav")

final_clip = video_clip.set_audio(audio_clip)
final_clip.write_videofile("final_output.mp4", codec="libx264")

print("Video saved successfully.")
