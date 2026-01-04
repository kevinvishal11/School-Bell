import pygame
import os
import time

def test_audio():
    print("Initializing Pygame Mixer...")
    try:
        pygame.mixer.init()
        print("Mixer initialized successfully.")
    except Exception as e:
        print(f"FAILED to initialize mixer: {e}")
        return

    # Check for sound files
    sound_file = os.path.join("sounds", "short_bell.wav")
    if not os.path.exists(sound_file):
        print(f"Sound file not found: {sound_file}")
        # Try finding any wav file
        if os.path.exists("sounds"):
            files = [f for f in os.listdir("sounds") if f.endswith(".wav")]
            if files:
                sound_file = os.path.join("sounds", files[0])
                print(f"Falling back to: {sound_file}")
            else:
                print("No .wav files found in sounds/ directory.")
                return
        else:
            print("sounds/ directory missing.")
            return

    print(f"Loading sound: {sound_file}")
    try:
        pygame.mixer.music.load(sound_file)
        print("Playing...")
        pygame.mixer.music.play()
        
        # Wait for a few seconds to let it play
        time.sleep(5)
        
        print("Stopping...")
        pygame.mixer.music.stop()
        print("Done.")
    except Exception as e:
        print(f"Playback failed: {e}")

if __name__ == "__main__":
    test_audio()
