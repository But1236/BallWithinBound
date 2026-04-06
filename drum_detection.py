"""
Enhanced drum beat detection algorithm for pre-recorded music files.
This implementation uses a pattern-based approach to detect drum beats
in music with a strong rhythmic structure.
"""

import numpy as np
import math

class DrumDetector:
    def __init__(self, sample_rate=44100, window_size=1024, history_length=4096, 
                 threshold_multiplier=1.1, cooldown_period=0.05, bpm_hint=76):
        """
        Initialize the drum detector.
        
        Args:
            sample_rate: Audio sample rate (Hz)
            window_size: Size of audio analysis window
            history_length: Number of samples to keep in history for background noise estimation
            threshold_multiplier: Multiplier for beat detection threshold (lower = more sensitive)
            cooldown_period: Minimum time between beats (seconds) (lower = more frequent detection)
            bpm_hint: Expected BPM of the music (used for pattern matching)
        """
        self.sample_rate = sample_rate
        self.window_size = window_size
        self.history_length = history_length
        self.threshold_multiplier = threshold_multiplier
        self.cooldown_period = cooldown_period
        self.bpm_hint = bpm_hint
        
        # History buffers
        self.energy_history = []
        self.beat_timestamps = []
        self.onset_history = []  # History of onset detections
        
        # State variables
        self.last_beat_time = 0
        self.background_energy = 0
        self.last_onset_time = 0
        
        # Pattern matching parameters
        self.expected_interval = 60.0 / bpm_hint  # Expected time between beats
        self.pattern_tolerance = 0.25  # Tolerance for pattern matching (25% - more tolerant)
        
    def compute_energy(self, audio_frame):
        """
        Compute the energy of an audio frame.
        
        Args:
            audio_frame: Array of audio samples
            
        Returns:
            Energy value (RMS)
        """
        if len(audio_frame) == 0:
            return 0
            
        # Calculate RMS energy
        energy = np.sqrt(np.mean(np.square(audio_frame)))
        return energy
    
    def compute_spectral_flux(self, audio_frame, prev_frame=None):
        """
        Compute spectral flux between consecutive frames.
        Spectral flux is sensitive to transients like drum hits.
        
        Args:
            audio_frame: Current audio frame
            prev_frame: Previous audio frame
            
        Returns:
            Spectral flux value
        """
        if prev_frame is None or len(audio_frame) == 0 or len(prev_frame) == 0:
            return 0
            
        # Compute FFT of both frames
        fft_current = np.fft.fft(audio_frame)
        fft_prev = np.fft.fft(prev_frame)
        
        # Calculate spectral difference
        diff = np.abs(fft_current) - np.abs(fft_prev)
        
        # Only count positive differences (flux increase)
        flux = np.sum(np.maximum(diff, 0))
        
        return flux
    
    def update_background_energy(self, energy):
        """
        Update the background energy estimate using a moving average.
        
        Args:
            energy: New energy value
        """
        self.energy_history.append(energy)
        
        # Keep only the most recent history
        if len(self.energy_history) > self.history_length:
            self.energy_history = self.energy_history[-self.history_length:]
        
        # Calculate median energy as background estimate
        if len(self.energy_history) > 0:
            self.background_energy = np.median(self.energy_history)
    
    def is_onset(self, current_time, energy, spectral_flux):
        """
        Detect if there's an onset (potential drum hit) at the current time.
        
        Args:
            current_time: Current time in seconds
            energy: Current energy value
            spectral_flux: Spectral flux value
            
        Returns:
            Boolean indicating if an onset is detected
        """
        # Check cooldown period
        if current_time - self.last_onset_time < self.cooldown_period / 2:
            return False
            
        # Combine energy and spectral flux for onset detection
        # Normalize spectral flux by energy to make it relative
        combined_metric = energy + (spectral_flux / max(energy, 1e-10)) * 0.5
        
        # Check if combined metric exceeds threshold
        threshold = self.background_energy * self.threshold_multiplier * 0.8
        if combined_metric > threshold and self.background_energy > 0:
            self.last_onset_time = current_time
            return True
            
        return False
    
    def is_beat(self, current_time, energy, spectral_flux):
        """
        Determine if the current energy represents a beat using pattern matching.
        
        Args:
            current_time: Current time in seconds
            energy: Current energy value
            spectral_flux: Spectral flux value
            
        Returns:
            Boolean indicating if a beat is detected
        """
        # First check for onset
        if not self.is_onset(current_time, energy, spectral_flux):
            return False
            
        # Check cooldown period for beats
        if current_time - self.last_beat_time < self.cooldown_period:
            return False
            
        # Pattern matching approach
        # If we have previous beats, check if current onset matches expected pattern
        if len(self.beat_timestamps) >= 2:
            # Calculate recent beat interval
            recent_interval = self.beat_timestamps[-1] - self.beat_timestamps[-2]
            
            # If recent interval is consistent, use it for prediction
            if abs(recent_interval - self.expected_interval) < self.pattern_tolerance * self.expected_interval:
                self.expected_interval = recent_interval
                
            # Predict next beat time
            predicted_next_beat = self.beat_timestamps[-1] + self.expected_interval
            
            # Check if current onset is close to predicted beat
            time_to_predicted = abs(current_time - predicted_next_beat)
            if time_to_predicted < self.pattern_tolerance * self.expected_interval:
                # Strong beat detected
                self.last_beat_time = current_time
                self.beat_timestamps.append(current_time)
                
                # Keep only recent timestamps
                while (len(self.beat_timestamps) > 0 and 
                       current_time - self.beat_timestamps[0] > 10.0):
                    self.beat_timestamps.pop(0)
                    
                return True
        else:
            # For first few beats, use simpler threshold-based detection
            threshold = self.background_energy * self.threshold_multiplier
            combined_metric = energy + spectral_flux * 0.1
            
            if combined_metric > threshold and self.background_energy > 0:
                # Beat detected
                self.last_beat_time = current_time
                self.beat_timestamps.append(current_time)
                return True
                
        return False
    
    def detect_beat(self, audio_frame, current_time, prev_frame=None):
        """
        Main function to detect drum beats in an audio frame.
        
        Args:
            audio_frame: Array of audio samples
            current_time: Current time in seconds
            prev_frame: Previous audio frame (for spectral flux calculation)
            
        Returns:
            Boolean indicating if a beat is detected
        """
        # Compute energy of the current frame
        energy = self.compute_energy(audio_frame)
        
        # Compute spectral flux
        spectral_flux = self.compute_spectral_flux(audio_frame, prev_frame)
        
        # Update background energy estimate
        self.update_background_energy(energy)
        
        # Check for beat
        beat_detected = self.is_beat(current_time, energy, spectral_flux)
        
        return beat_detected
    
    def get_recent_bpm(self, current_time, window=5.0):
        """
        Calculate BPM based on recent beats.
        
        Args:
            current_time: Current time in seconds
            window: Time window to consider for BPM calculation (seconds)
            
        Returns:
            Estimated BPM, or 0 if not enough data
        """
        # Filter recent beats
        recent_beats = [t for t in self.beat_timestamps 
                       if current_time - t <= window]
        
        # Need at least 2 beats to calculate BPM
        if len(recent_beats) < 2:
            return 0
            
        # Calculate average time between beats
        intervals = [recent_beats[i+1] - recent_beats[i] 
                    for i in range(len(recent_beats)-1)]
        avg_interval = np.mean(intervals)
        
        # Convert to BPM (beats per minute)
        if avg_interval > 0:
            return 60.0 / avg_interval
            
        return 0

# Example usage
if __name__ == "__main__":
    # Create detector
    detector = DrumDetector(bpm_hint=76)
    
    # Simulate audio processing
    sample_rate = 44100
    frame_size = 1024
    frame_duration = frame_size / sample_rate
    
    # Generate test signal with beats
    prev_frame = None
    for i in range(1000):
        current_time = i * frame_duration
        
        # Create audio frame (simulated)
        if i % 50 == 0:  # Simulate beats every 50 frames (more frequent)
            # Higher energy frame to simulate beat
            audio_frame = np.random.normal(0, 0.5, frame_size)
        else:
            # Normal energy frame
            audio_frame = np.random.normal(0, 0.1, frame_size)
        
        # Detect beat
        beat = detector.detect_beat(audio_frame, current_time, prev_frame)
        prev_frame = audio_frame.copy()
        
        if beat:
            bpm = detector.get_recent_bpm(current_time)
            print(f"Beat detected at {current_time:.3f}s, BPM: {bpm:.1f}")
