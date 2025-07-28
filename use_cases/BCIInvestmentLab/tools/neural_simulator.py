"""
🧠 NeuralSimulatorTool - Synthetic Neural Signal Generation
========================================================

Domain-specific tool for generating synthetic neural signals for BCI research.
Demonstrates Code node capabilities and scientific computing.

## Use Case
🧠 Brain-Computer Interface research
🧠 Neural signal processing validation
🧠 Algorithm testing with controlled data
🧠 EEG/fMRI simulation for development

## Features
- Synthetic EEG signal generation
- Multiple brain wave patterns (alpha, beta, gamma, theta, delta)
- Noise simulation and artifacts
- Statistical validation of generated signals
- Export in multiple formats
"""

import math
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import json

from ice_sdk.tools.base import ToolBase
import structlog

logger = structlog.get_logger(__name__)


class NeuralSimulatorTool(ToolBase):
    """Generate synthetic neural signals for BCI research and testing.
    
    This tool creates realistic synthetic EEG/neural data that can be used
    for algorithm development, testing, and validation in neuroscience research.
    """
    
    name: str = "neural_simulator"
    description: str = "Generate synthetic neural signals for BCI research and testing"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Execute neural signal simulation.
        
        Args:
            signal_type: Type of neural signal - 'eeg', 'fmri', 'mixed' (default: 'eeg')
            duration: Duration in seconds (default: 10.0)
            sampling_rate: Sampling rate in Hz (default: 256)
            channels: Number of channels (default: 64)
            noise_level: Noise level 0.0-1.0 (default: 0.1)
            brain_states: List of brain states to simulate (default: ['resting', 'active'])
            frequency_bands: Frequency bands to include (default: ['alpha', 'beta', 'gamma'])
            artifacts: Whether to include artifacts (default: True)
            export_format: Export format - 'json', 'array', 'detailed' (default: 'detailed')
            
        Returns:
            Dict containing synthetic neural signals and metadata
        """
        try:
            # Extract and validate parameters
            signal_type = kwargs.get("signal_type", "eeg")
            duration = kwargs.get("duration", 10.0)
            sampling_rate = kwargs.get("sampling_rate", 256)
            channels = kwargs.get("channels", 64)
            noise_level = kwargs.get("noise_level", 0.1)
            brain_states = kwargs.get("brain_states", ["resting", "active"])
            frequency_bands = kwargs.get("frequency_bands", ["alpha", "beta", "gamma"])
            artifacts = kwargs.get("artifacts", True)
            export_format = kwargs.get("export_format", "detailed")
            
            logger.info(f"Generating {signal_type} signals: {duration}s, {channels} channels, {sampling_rate}Hz")
            
            # Calculate signal parameters
            total_samples = int(duration * sampling_rate)
            time_points = [i / sampling_rate for i in range(total_samples)]
            
            # Generate base signals for each channel
            channel_data = {}
            for channel in range(channels):
                channel_name = self._get_channel_name(channel, signal_type)
                signal = self._generate_channel_signal(
                    time_points, channel, frequency_bands, brain_states, 
                    signal_type, noise_level, artifacts
                )
                channel_data[channel_name] = signal
            
            # Generate events and markers
            events = self._generate_events(duration, brain_states)
            
            # Calculate signal statistics
            statistics = self._calculate_signal_statistics(channel_data, sampling_rate, frequency_bands)
            
            # Generate analysis and insights
            analysis = self._analyze_neural_patterns(channel_data, events, frequency_bands)
            
            # Format output based on export_format
            if export_format == "array":
                output_data = {
                    "signals": list(channel_data.values()),
                    "time_points": time_points,
                    "channel_names": list(channel_data.keys())
                }
            elif export_format == "json":
                output_data = {
                    "signals": channel_data,
                    "time_points": time_points,
                    "events": events
                }
            else:  # detailed
                output_data = {
                    "signals": channel_data,
                    "time_points": time_points,
                    "events": events,
                    "statistics": statistics,
                    "analysis": analysis,
                    "metadata": {
                        "signal_type": signal_type,
                        "duration": duration,
                        "sampling_rate": sampling_rate,
                        "channels": channels,
                        "total_samples": total_samples,
                        "noise_level": noise_level,
                        "brain_states": brain_states,
                        "frequency_bands": frequency_bands,
                        "artifacts_included": artifacts
                    }
                }
            
            return {
                "neural_data": output_data,
                "generation_summary": {
                    "signal_type": signal_type,
                    "channels_generated": len(channel_data),
                    "duration_seconds": duration,
                    "total_data_points": total_samples * channels,
                    "events_generated": len(events),
                    "quality_score": self._assess_signal_quality(channel_data, noise_level)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"NeuralSimulatorTool execution failed: {e}")
            return {
                "error": str(e),
                "neural_data": {},
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_channel_name(self, channel_index: int, signal_type: str) -> str:
        """Generate realistic channel names based on signal type."""
        if signal_type == "eeg":
            # Standard EEG electrode positions (10-20 system)
            eeg_positions = [
                "Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "FC5", "FC1", "FC2", "FC6",
                "T7", "C3", "Cz", "C4", "T8", "TP9", "CP5", "CP1", "CP2", "CP6", "TP10",
                "P7", "P3", "Pz", "P4", "P8", "PO9", "O1", "Oz", "O2", "PO10",
                "AF7", "AF3", "AF4", "AF8", "F5", "F1", "F2", "F6", "FT9", "FT7", "FC3",
                "FC4", "FT8", "FT10", "C5", "C1", "C2", "C6", "TP7", "CP3", "CPz", "CP4",
                "TP8", "P5", "P1", "P2", "P6", "PO7", "PO3", "POz", "PO4", "PO8"
            ]
            return eeg_positions[channel_index % len(eeg_positions)]
        elif signal_type == "fmri":
            return f"ROI_{channel_index + 1:03d}"
        else:
            return f"CH_{channel_index + 1:03d}"
    
    def _generate_channel_signal(self, time_points: List[float], channel: int, 
                                frequency_bands: List[str], brain_states: List[str],
                                signal_type: str, noise_level: float, artifacts: bool) -> List[float]:
        """Generate realistic neural signal for a single channel."""
        signal = [0.0] * len(time_points)
        
        # Define frequency band characteristics
        band_frequencies = {
            "delta": (1, 4),      # Deep sleep, unconscious
            "theta": (4, 8),      # Drowsiness, REM sleep, meditation
            "alpha": (8, 13),     # Relaxed awareness, eyes closed
            "beta": (13, 30),     # Normal consciousness, active thinking
            "gamma": (30, 100)    # High-level cognitive processing
        }
        
        # Generate base oscillations for each frequency band
        for band in frequency_bands:
            if band in band_frequencies:
                freq_min, freq_max = band_frequencies[band]
                
                # Random frequency within band
                frequency = random.uniform(freq_min, freq_max)
                
                # Amplitude varies by brain state and channel location
                amplitude = self._get_band_amplitude(band, channel, brain_states, signal_type)
                
                # Generate sinusoidal oscillation with some phase variation
                phase = random.uniform(0, 2 * math.pi)
                for i, t in enumerate(time_points):
                    signal[i] += amplitude * math.sin(2 * math.pi * frequency * t + phase)
        
        # Add brain state transitions
        signal = self._add_brain_state_transitions(signal, time_points, brain_states)
        
        # Add realistic noise
        if noise_level > 0:
            signal = self._add_noise(signal, noise_level)
        
        # Add artifacts if requested
        if artifacts:
            signal = self._add_artifacts(signal, time_points, channel)
        
        return signal
    
    def _get_band_amplitude(self, band: str, channel: int, brain_states: List[str], signal_type: str) -> float:
        """Get realistic amplitude for frequency band based on channel location and brain state."""
        base_amplitudes = {
            "delta": 50.0,
            "theta": 30.0,
            "alpha": 20.0,
            "beta": 15.0,
            "gamma": 5.0
        }
        
        base_amp = base_amplitudes.get(band, 10.0)
        
        # Modulate by brain state
        if "active" in brain_states:
            if band in ["beta", "gamma"]:
                base_amp *= 1.5  # Increase high-frequency activity
            elif band in ["alpha", "theta"]:
                base_amp *= 0.7  # Decrease low-frequency activity
        
        # Add channel-specific variation
        channel_factor = 0.8 + 0.4 * random.random()  # 0.8 to 1.2
        
        # Add some spatial organization (frontal, central, parietal, occipital)
        if signal_type == "eeg":
            if channel < 16:  # Frontal
                if band == "beta":
                    channel_factor *= 1.2
            elif channel < 32:  # Central
                if band == "alpha":
                    channel_factor *= 1.3
            else:  # Posterior
                if band == "alpha":
                    channel_factor *= 1.5
        
        return base_amp * channel_factor
    
    def _add_brain_state_transitions(self, signal: List[float], time_points: List[float], brain_states: List[str]) -> List[float]:
        """Add realistic transitions between brain states."""
        if len(brain_states) <= 1:
            return signal
        
        # Create state transition points
        total_duration = time_points[-1] if time_points else 10.0
        state_duration = total_duration / len(brain_states)
        
        modified_signal = signal.copy()
        
        for i, state in enumerate(brain_states):
            start_time = i * state_duration
            end_time = (i + 1) * state_duration
            
            # Find corresponding sample indices
            start_idx = int(start_time * len(time_points) / total_duration)
            end_idx = int(end_time * len(time_points) / total_duration)
            
            # Apply state-specific modulation
            state_factor = self._get_state_modulation(state)
            
            for j in range(start_idx, min(end_idx, len(modified_signal))):
                modified_signal[j] *= state_factor
        
        return modified_signal
    
    def _get_state_modulation(self, state: str) -> float:
        """Get amplitude modulation factor for brain state."""
        state_factors = {
            "resting": 1.0,
            "active": 1.3,
            "relaxed": 0.8,
            "focused": 1.2,
            "drowsy": 0.6,
            "alert": 1.4
        }
        return state_factors.get(state, 1.0)
    
    def _add_noise(self, signal: List[float], noise_level: float) -> List[float]:
        """Add realistic neural noise to the signal."""
        noisy_signal = []
        signal_std = self._calculate_std(signal) if signal else 1.0
        
        for value in signal:
            # Gaussian noise
            noise = random.gauss(0, noise_level * signal_std)
            noisy_signal.append(value + noise)
        
        return noisy_signal
    
    def _add_artifacts(self, signal: List[float], time_points: List[float], channel: int) -> List[float]:
        """Add realistic artifacts (eye blinks, muscle activity, etc.)."""
        artifacted_signal = signal.copy()
        
        # Eye blink artifacts (more prominent in frontal channels)
        if channel < 8:  # Frontal channels
            blink_probability = 0.001  # 0.1% chance per sample
            blink_amplitude = 100.0
            
            i = 0
            while i < len(artifacted_signal):
                if random.random() < blink_probability:
                    # Add blink artifact (lasts ~200ms)
                    blink_duration = int(0.2 * len(time_points) / time_points[-1]) if time_points else 10
                    for j in range(i, min(i + blink_duration, len(artifacted_signal))):
                        # Exponential decay
                        decay_factor = math.exp(-(j - i) / (blink_duration / 3))
                        artifacted_signal[j] += blink_amplitude * decay_factor
                    i += blink_duration
                else:
                    i += 1
        
        # Muscle artifacts (random high-frequency bursts)
        muscle_probability = 0.0005
        for i in range(len(artifacted_signal)):
            if random.random() < muscle_probability:
                # Add brief high-frequency burst
                burst_duration = random.randint(5, 20)
                burst_amplitude = random.uniform(20, 50)
                for j in range(i, min(i + burst_duration, len(artifacted_signal))):
                    artifacted_signal[j] += burst_amplitude * random.uniform(-1, 1)
        
        return artifacted_signal
    
    def _generate_events(self, duration: float, brain_states: List[str]) -> List[Dict[str, Any]]:
        """Generate realistic events and markers."""
        events = []
        
        # Brain state change events
        state_duration = duration / len(brain_states)
        for i, state in enumerate(brain_states):
            event_time = i * state_duration
            events.append({
                "time": event_time,
                "type": "brain_state_change",
                "description": f"Transition to {state} state",
                "duration": state_duration,
                "state": state
            })
        
        # Simulated task events
        task_events = ["stimulus_presentation", "response_cue", "feedback", "rest_period"]
        num_events = random.randint(3, 8)
        
        for _ in range(num_events):
            event_time = random.uniform(0, duration)
            event_type = random.choice(task_events)
            events.append({
                "time": event_time,
                "type": event_type,
                "description": f"Simulated {event_type.replace('_', ' ')}",
                "duration": random.uniform(0.5, 3.0)
            })
        
        # Sort events by time
        events.sort(key=lambda x: x["time"])
        
        return events
    
    def _calculate_signal_statistics(self, channel_data: Dict[str, List[float]], 
                                   sampling_rate: int, frequency_bands: List[str]) -> Dict[str, Any]:
        """Calculate comprehensive statistics for the generated signals."""
        all_values = []
        for channel_signal in channel_data.values():
            all_values.extend(channel_signal)
        
        if not all_values:
            return {"error": "No signal data to analyze"}
        
        # Basic statistics
        mean_val = sum(all_values) / len(all_values)
        min_val = min(all_values)
        max_val = max(all_values)
        
        # Calculate standard deviation
        variance = sum((x - mean_val) ** 2 for x in all_values) / len(all_values)
        std_val = math.sqrt(variance)
        
        # Per-channel statistics
        channel_stats = {}
        for channel_name, signal in channel_data.items():
            if signal:
                channel_mean = sum(signal) / len(signal)
                channel_std = math.sqrt(sum((x - channel_mean) ** 2 for x in signal) / len(signal))
                channel_stats[channel_name] = {
                    "mean": channel_mean,
                    "std": channel_std,
                    "min": min(signal),
                    "max": max(signal),
                    "range": max(signal) - min(signal)
                }
        
        return {
            "overall": {
                "mean": mean_val,
                "std": std_val,
                "min": min_val,
                "max": max_val,
                "range": max_val - min_val,
                "total_samples": len(all_values)
            },
            "per_channel": channel_stats,
            "signal_quality": {
                "snr_estimate": abs(mean_val) / std_val if std_val > 0 else 0,
                "dynamic_range": max_val - min_val,
                "amplitude_variability": std_val / abs(mean_val) if mean_val != 0 else float('inf')
            }
        }
    
    def _analyze_neural_patterns(self, channel_data: Dict[str, List[float]], 
                               events: List[Dict[str, Any]], frequency_bands: List[str]) -> Dict[str, Any]:
        """Analyze neural patterns and provide insights."""
        
        # Analyze synchronization between channels
        synchronization = self._analyze_channel_synchronization(channel_data)
        
        # Analyze frequency content
        frequency_analysis = self._analyze_frequency_content(channel_data, frequency_bands)
        
        # Event-related analysis
        event_analysis = self._analyze_event_related_patterns(channel_data, events)
        
        return {
            "synchronization": synchronization,
            "frequency_analysis": frequency_analysis,
            "event_analysis": event_analysis,
            "neural_insights": self._generate_neural_insights(frequency_analysis, synchronization)
        }
    
    def _analyze_channel_synchronization(self, channel_data: Dict[str, List[float]]) -> Dict[str, Any]:
        """Analyze synchronization between channels."""
        channels = list(channel_data.keys())
        if len(channels) < 2:
            return {"error": "Need at least 2 channels for synchronization analysis"}
        
        # Calculate correlation between channels (simplified)
        correlations = {}
        high_sync_pairs = []
        
        for i, ch1 in enumerate(channels[:5]):  # Limit to first 5 channels for performance
            for ch2 in channels[i+1:6]:
                signal1 = channel_data[ch1]
                signal2 = channel_data[ch2]
                
                if len(signal1) == len(signal2) and len(signal1) > 0:
                    correlation = self._calculate_correlation(signal1, signal2)
                    correlations[f"{ch1}-{ch2}"] = correlation
                    
                    if abs(correlation) > 0.7:
                        high_sync_pairs.append((ch1, ch2, correlation))
        
        return {
            "correlations": correlations,
            "high_synchronization_pairs": high_sync_pairs,
            "avg_synchronization": sum(correlations.values()) / len(correlations) if correlations else 0
        }
    
    def _analyze_frequency_content(self, channel_data: Dict[str, List[float]], frequency_bands: List[str]) -> Dict[str, Any]:
        """Analyze frequency content of signals."""
        
        # Simple frequency analysis (power estimation)
        band_powers = {}
        
        for band in frequency_bands:
            total_power = 0
            channel_count = 0
            
            for channel_name, signal in channel_data.items():
                if signal:
                    # Estimate power in frequency band (simplified approach)
                    band_power = self._estimate_band_power(signal, band)
                    total_power += band_power
                    channel_count += 1
            
            if channel_count > 0:
                band_powers[band] = total_power / channel_count
        
        # Determine dominant frequency band
        dominant_band = max(band_powers.keys(), key=lambda k: band_powers[k]) if band_powers else None
        
        return {
            "band_powers": band_powers,
            "dominant_band": dominant_band,
            "power_distribution": {
                band: power / sum(band_powers.values()) * 100 
                for band, power in band_powers.items()
            } if band_powers else {}
        }
    
    def _analyze_event_related_patterns(self, channel_data: Dict[str, List[float]], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns related to events."""
        
        event_responses = {}
        
        for event in events:
            event_type = event["type"]
            event_time = event["time"]
            
            # Calculate average response around event time
            # (This is a simplified event-related potential analysis)
            if event_type not in event_responses:
                event_responses[event_type] = {"count": 0, "avg_amplitude": 0}
            
            event_responses[event_type]["count"] += 1
            # In a real implementation, we would extract signal segments around the event
            
        return {
            "event_types": list(event_responses.keys()),
            "event_responses": event_responses,
            "total_events": len(events)
        }
    
    def _generate_neural_insights(self, frequency_analysis: Dict[str, Any], synchronization: Dict[str, Any]) -> List[str]:
        """Generate insights about the neural patterns."""
        insights = []
        
        # Frequency insights
        if frequency_analysis.get("dominant_band"):
            band = frequency_analysis["dominant_band"]
            insights.append(f"Dominant frequency band is {band}, suggesting neural activity consistent with this brain state")
        
        # Synchronization insights
        avg_sync = synchronization.get("avg_synchronization", 0)
        if avg_sync > 0.5:
            insights.append("High inter-channel synchronization detected, indicating coordinated neural activity")
        elif avg_sync < 0.2:
            insights.append("Low inter-channel synchronization, suggesting independent neural processes")
        
        # Power distribution insights
        power_dist = frequency_analysis.get("power_distribution", {})
        if power_dist.get("gamma", 0) > 30:
            insights.append("High gamma power suggests active cognitive processing")
        if power_dist.get("alpha", 0) > 40:
            insights.append("High alpha power indicates relaxed, meditative state")
        
        return insights
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        return math.sqrt(variance)
    
    def _calculate_correlation(self, signal1: List[float], signal2: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(signal1) != len(signal2) or len(signal1) < 2:
            return 0
        
        n = len(signal1)
        mean1 = sum(signal1) / n
        mean2 = sum(signal2) / n
        
        numerator = sum((signal1[i] - mean1) * (signal2[i] - mean2) for i in range(n))
        
        sum_sq1 = sum((signal1[i] - mean1) ** 2 for i in range(n))
        sum_sq2 = sum((signal2[i] - mean2) ** 2 for i in range(n))
        
        denominator = math.sqrt(sum_sq1 * sum_sq2)
        
        return numerator / denominator if denominator != 0 else 0
    
    def _estimate_band_power(self, signal: List[float], band: str) -> float:
        """Estimate power in a frequency band (simplified)."""
        # This is a very simplified power estimation
        # In practice, you'd use FFT or other spectral methods
        
        if not signal:
            return 0
        
        # Simple variance-based power estimate
        mean_val = sum(signal) / len(signal)
        power = sum((x - mean_val) ** 2 for x in signal) / len(signal)
        
        # Weight by frequency band (higher frequencies typically have lower power)
        band_weights = {
            "delta": 1.0,
            "theta": 0.8,
            "alpha": 0.6,
            "beta": 0.4,
            "gamma": 0.2
        }
        
        return power * band_weights.get(band, 0.5)
    
    def _assess_signal_quality(self, channel_data: Dict[str, List[float]], noise_level: float) -> float:
        """Assess overall quality of generated signals."""
        # Simple quality score based on signal characteristics
        base_score = 1.0 - noise_level  # Lower noise = higher quality
        
        # Check for reasonable amplitude range
        all_values = []
        for signal in channel_data.values():
            all_values.extend(signal)
        
        if all_values:
            signal_range = max(all_values) - min(all_values)
            if 10 < signal_range < 1000:  # Reasonable EEG amplitude range
                base_score += 0.2
        
        # Check for channel count
        if len(channel_data) >= 32:
            base_score += 0.1
        
        return min(base_score, 1.0)

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return the input schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "signal_type": {
                    "type": "string",
                    "enum": ["eeg", "fmri", "mixed"],
                    "default": "eeg",
                    "description": "Type of neural signal to generate"
                },
                "duration": {
                    "type": "number",
                    "default": 10.0,
                    "minimum": 1.0,
                    "maximum": 300.0,
                    "description": "Duration of signal in seconds"
                },
                "sampling_rate": {
                    "type": "integer",
                    "default": 256,
                    "minimum": 64,
                    "maximum": 2048,
                    "description": "Sampling rate in Hz"
                },
                "channels": {
                    "type": "integer",
                    "default": 64,
                    "minimum": 1,
                    "maximum": 256,
                    "description": "Number of channels"
                },
                "noise_level": {
                    "type": "number",
                    "default": 0.1,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Noise level (0.0 = no noise, 1.0 = high noise)"
                },
                "brain_states": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["resting", "active"],
                    "description": "Brain states to simulate"
                },
                "frequency_bands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["alpha", "beta", "gamma"],
                    "description": "Frequency bands to include"
                },
                "artifacts": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include realistic artifacts"
                },
                "export_format": {
                    "type": "string",
                    "enum": ["json", "array", "detailed"],
                    "default": "detailed",
                    "description": "Export format for the data"
                }
            }
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return the output schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "neural_data": {
                    "type": "object",
                    "description": "Generated neural signal data"
                },
                "generation_summary": {
                    "type": "object",
                    "description": "Summary of signal generation process"
                },
                "timestamp": {
                    "type": "string",
                    "description": "When the signals were generated"
                }
            }
        } 