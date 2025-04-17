import cv2
import moviepy.editor as mp
import pyaudio
import wave
import threading
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
import os
import time
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_audioclips, AudioClip

# Function to list available audio devices
def list_audio_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    print("Available audio devices:")
    for i in range(0, numdevices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        print(f"Device {i}: {device_info['name']}, Channels: {device_info['maxInputChannels']}")
    p.terminate()

# Function to mute target words in audio
def mute_target_words(audio_path, target_words):
    recognizer = sr.Recognizer()
    sound = AudioSegment.from_file(audio_path)
    
    segment_length = 1500  # 1.5-second segments
    silence = AudioSegment.silent(duration=segment_length)  # 1.5 seconds of silence
    modified_audio = AudioSegment.empty()
    
    temp_dir = tempfile.mkdtemp()  # Create a temporary directory
    try:
        for i in range(0, len(sound), segment_length):
            segment = sound[i:i+segment_length]
            temp_audio_file = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".wav", delete=False)
            segment.export(temp_audio_file.name, format="wav")
            
            with sr.AudioFile(temp_audio_file.name) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.record(source)
            
            try:
                text = recognizer.recognize_google(audio)
                words = text.split()
                word_durations = segment.duration_seconds / len(words) if words else segment.duration_seconds
                print(f"Segment {i // segment_length}: '{text}'")
                for j, word in enumerate(words):
                    start_time = i / 1000 + j * word_durations
                    end_time = start_time + word_durations
                    print(f"Word: '{word}', Start Time: {start_time:.2f}s, End Time: {end_time:.2f}s")
                
                if any(word.lower() in text.lower() for word in target_words):
                    modified_audio += silence
                    print(f"Muting segment {i // segment_length} for words: {', '.join([word for word in target_words if word.lower() in text.lower()])}")
                else:
                    modified_audio += segment
            except sr.UnknownValueError:
                modified_audio += segment
                print(f"Segment {i // segment_length}: Could not understand audio")
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")
            finally:
                temp_audio_file.close()
    finally:
        # Clean up temporary files
        for temp_file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, temp_file))
        os.rmdir(temp_dir)
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_modified_audio_file:
        modified_audio.export(temp_modified_audio_file.name, format="wav")
    
    return temp_modified_audio_file.name

# Function to record audio
def record_audio(filename, duration, channels=1):
    chunk = 1024  # Record in chunks of 1024 samples
    sample_format = pyaudio.paInt16  # 16 bits per sample
    fs = 44100  # Record at 44100 samples per second

    p = pyaudio.PyAudio()  # Create an interface to PortAudio

    print('Recording audio...')

    stream = p.open(format=sample_format,
                    channels=channels,
                    rate=fs,
                    frames_per_buffer=chunk,
                    input=True)

    frames = []  # Initialize array to store frames

    for _ in range(0, int(fs / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)

    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()

    print('Finished recording audio.')

    # Save the recorded data as a WAV file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))

# Function to capture video and process audio
def capture_and_process_video(output_filename, target_words, duration=18):
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open video capture")
        return
    
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('temp_video.avi', fourcc, 20.0, (640, 480))
    
    frames = []
    start_time = time.time()
    print(f"Recording for {duration} seconds. Press 'q' to stop early.")
    
    # Start audio recording in a separate thread
    audio_filename = 'temp_audio.wav'
    audio_thread = threading.Thread(target=record_audio, args=(audio_filename, duration))
    audio_thread.start()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
            out.write(frame)  # Write the frame to the video file
            cv2.imshow('frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q') or (time.time() - start_time) > duration:
                break
        else:
            break
    
    cap.release()
    out.release()  # Release the VideoWriter object
    cv2.destroyAllWindows()
    
    audio_thread.join()  # Ensure audio recording is complete
    
    # Check if video file was created
    if not os.path.exists('temp_video.avi'):
        print("Error: Video file was not created.")
        return
    
    # Create a video clip from the captured frames
    try:
        video_clip = mp.VideoFileClip('temp_video.avi')
    except Exception as e:
        print(f"Error loading video file: {e}")
        return

    # Speed up the video by 40%
    video_clip = video_clip.fx(mp.vfx.speedx, 1.4)
    
    # Mute target words in the audio
    modified_audio_path = mute_target_words(audio_filename, target_words)
    
    # Create final video with modified audio
    try:
        modified_audio = mp.AudioFileClip(modified_audio_path)
        final_video = video_clip.set_audio(modified_audio)
        final_video.write_videofile(output_filename, codec='libx264')
        print(f"Final video saved to: {output_filename}")
        final_video.close()  # Ensure the final_video object is closed
    except Exception as e:
        print(f"Error creating final video: {e}")
        return
    
    # Clean up temporary files
    os.remove('temp_video.avi')
    os.remove(audio_filename)
    os.remove(modified_audio_path)
    print("Temporary files cleaned up.")

if __name__ == "__main__":
    list_audio_devices()
    target_words = ["example", "target", "fuck"]
    output_filename = "output_video.mp4"
    capture_and_process_video(output_filename, target_words, duration=18)
    print(f"Output video is located at: {output_filename}")
