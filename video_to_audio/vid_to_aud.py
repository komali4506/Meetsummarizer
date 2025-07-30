from moviepy.video.io.VideoFileClip import VideoFileClip

# Load the video file
video = VideoFileClip("video.mp4")

# Extract and save the audio
video.audio.write_audiofile("audio_output.mp3") 
