import os
import logging
import sys
import time
import torch
import librosa
import numpy as np
import soundfile as sf
from celery import Celery
from celery import Task
from librosa import LibrosaError
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Dense, Dropout

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


class PredictTask(Task):
    def __init__(self):
        super().__init__()
        self.model_gender = None
        self.USE_ONNX = False
        self.model, self.utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=True,
            onnx=self.USE_ONNX,
        )
        (
            self.get_speech_timestamps,
            self.save_audio,
            self.read_audio,
            self.VADIterator,
            self.collect_chunks,
        ) = self.utils

    def __call__(self, *args, **kwargs):
        if self.model_gender is None:
            try:
                model_path = os.getenv("MODEL_PATH", "./models/model.h5")
                if not os.path.exists(model_path):
                    raise FileNotFoundError(
                        f"No such file or directory: '{model_path}'"
                    )
                self.model_gender = self.create_model()
                self.model_gender.load_weights(model_path)
            except Exception as e:
                logging.error("Failed to initialize model: %s", str(e))
                exit(1)
        else:
            logging.warning("Model already initialized")
        return self.run(*args, **kwargs)

    def extract_feature(self, file_name, **kwargs):
        """
        Extract feature from audio file `file_name`
            Features supported:
                - MFCC (mfcc)
                - Chroma (chroma)
                - MEL Spectrogram Frequency (mel)
                - Contrast (contrast)
                - Tonnetz (tonnetz)
            e.g:
            `features = extract_feature(path, mel=True, mfcc=True)`
        """
        mfcc = kwargs.get("mfcc")
        chroma = kwargs.get("chroma")
        mel = kwargs.get("mel")
        contrast = kwargs.get("contrast")
        tonnetz = kwargs.get("tonnetz")
        X, sample_rate = librosa.core.load(file_name)
        if chroma or contrast:
            stft = np.abs(librosa.stft(X))
        result = np.array([])
        if mfcc:
            mfccs = np.mean(
                librosa.feature.mfcc(y=X, sr=sample_rate, n_mfcc=40).T, axis=0
            )
            result = np.hstack((result, mfccs))
        if chroma:
            chroma = np.mean(
                librosa.feature.chroma_stft(S=stft, sr=sample_rate).T, axis=0
            )
            result = np.hstack((result, chroma))
        if mel:
            mel = np.mean(librosa.feature.melspectrogram(y=X, sr=sample_rate).T, axis=0)
            result = np.hstack((result, mel))
        if contrast:
            contrast = np.mean(
                librosa.feature.spectral_contrast(S=stft, sr=sample_rate).T, axis=0
            )
            result = np.hstack((result, contrast))
        if tonnetz:
            tonnetz = np.mean(
                librosa.feature.tonnetz(
                    y=librosa.effects.harmonic(X), sr=sample_rate
                ).T,
                axis=0,
            )
            result = np.hstack((result, tonnetz))
        return result

    def check_operator(self, audio_title):
        # if file_path split with _ and first element is three digit number then it is operator number
        file_name = audio_title.split("_")[-1].split(".")[0]
        if len(file_name) == 3 and file_name.isdigit():
            return False
        else:
            return True

    def save_channel_one(self, file_path, audio_title):
        y, sr = librosa.load(file_path, mono=False)
        new_file_name = file_path.split("/")[-1].split(".")[0] + "_channel_1.mp3"
        new_file_path = os.path.join("uploads", new_file_name)
        duration = librosa.get_duration(filename=file_path)
        if self.check_operator(audio_title):
            client_channel = 1
        else:
            client_channel = 0
        channel_1 = y[client_channel]
        sf.write(new_file_path, data=channel_1, samplerate=sr)

        return new_file_path, duration

    from typing import Callable, List

    def collect_chunks(
        self, tss: List[dict], wav: torch.Tensor, sample_rate: int = 44100
    ):
        silence_duration = 0.0  # 0.3 seconds of silence
        silence_length = int(sample_rate * silence_duration)
        silence = torch.zeros(silence_length)

        chunks = []
        for i in tss:
            chunks.append(wav[i["start"] : i["end"]])
            chunks.append(silence)  # Append silence after each chunk

        # Remove the last added silence to avoid trailing silence
        chunks.pop()

        return torch.cat(chunks)

    def find_longest_duration(self, ranges):
        # Initialize the maximum duration and the corresponding item
        max_duration = 0
        longest_item = None

        # Loop through the list of dictionaries
        for item in ranges:
            # Calculate the duration for the current item
            duration = item["end"] - item["start"]

            # Update if the current duration is greater than the max found so far
            if duration > max_duration:
                max_duration = duration
                longest_item = item

        return longest_item

    def find_3_longest_durations(self, ranges):
        # Sort the ranges by duration in descending order
        sorted_ranges = sorted(
            ranges, key=lambda x: x["end"] - x["start"], reverse=True
        )

        # Return the top three items, or fewer if there aren't three items
        return sorted_ranges[:5]

    def save_only_speech(self, file_path, original_file_path):
        """
        RULES:
        - if using find_longest_duration, then wrap max_duration_chunk in a list
        - if using find_3_longest_durations, theh just use max_duration_chunk as is

        """

        # Read the audio file
        mp3 = self.read_audio(file_path, sampling_rate=16000)

        # Get speech timestamps using a model
        speech_timestamps = self.get_speech_timestamps(
            mp3, self.model, sampling_rate=16000, min_silence_duration_ms=5
        )
        # Find the speech chunk with the maximum duration
        max_duration_chunk = self.find_longest_duration(
            speech_timestamps
        )  # print the longest speech segment
        print("MAX DURATION CHUNK:", max_duration_chunk)
        # Create a new file name based on the original
        new_file_name = file_path.split("/")[-1].split(".")[0] + "_only_speech.mp3"
        new_file_path = os.path.join("uploads", new_file_name)
        original_file_path_parts = original_file_path.split("_")[4:]
        original_file_path_parts = ".".join(original_file_path_parts)
        original_file_path = os.path.join(
            original_file_path_parts + "_only_speech.mp3",
        )
        # Save the audio corresponding to the longest speech segment
        self.save_audio(
            new_file_path,
            self.collect_chunks([max_duration_chunk], mp3),
            sampling_rate=16000,
        )
        self.save_audio(
            original_file_path,
            self.collect_chunks([max_duration_chunk], mp3),
            sampling_rate=16000,
        )
        return new_file_path

    def create_model(self, vector_length=128):
        """5 hidden dense layers from 256 units to 64, not the best model, but not bad."""
        model = Sequential()
        model.add(Dense(256, input_shape=(vector_length,)))
        model.add(Dropout(0.3))
        model.add(Dense(256, activation="relu"))
        model.add(Dropout(0.3))
        model.add(Dense(128, activation="relu"))
        model.add(Dropout(0.3))
        model.add(Dense(128, activation="relu"))
        model.add(Dropout(0.3))
        model.add(Dense(64, activation="relu"))
        model.add(Dropout(0.3))
        # one output neuron with sigmoid activation function, 0 means female, 1 means male
        model.add(Dense(1, activation="sigmoid"))
        # using binary crossentropy as it's male/female classification (binary)
        model.compile(
            loss="binary_crossentropy", metrics=["accuracy"], optimizer="adam"
        )
        # print summary of the model
        model.summary()
        return model

    def classify_gender(self, file):
        try:
            audio_length = librosa.get_duration(filename=file)
            start = time.time()
            features = self.extract_feature(file, mel=True).reshape(1, -1)
            male_prob = self.model_gender.predict(features)[0][0]
            print("MALE PROB:", male_prob)
            female_prob = 1 - male_prob
            gender = "male" if male_prob > female_prob else "female"
            text = f"Result: Probabilities:     Male: {male_prob*100:.2f}%    Female: {female_prob*100:.2f}%"
            end = time.time()
            final_time = end - start

            result = {
                "gender": gender,
                "male_probability": f"{male_prob*100:.2f}%",
                "female_probability": f"{female_prob*100:.2f}%",
                "Time taken": f"{final_time:.2f} seconds",
                "Audio length": f"{audio_length:.2f} seconds",
            }

            return result
        except LibrosaError as e:
            logging.error("Failed to extract feature: %s", str(e))
            raise e
        except Exception as e:
            logging.error("Failed to classify gender: %s", str(e))
            raise e

    def classify_speaker_gender(self, audio_path, audio_title):
        audio_info = {}
        new_file_path_channel_only, duration = self.save_channel_one(
            audio_path, audio_title
        )
        new_file_path_speech_only = self.save_only_speech(
            new_file_path_channel_only, audio_path
        )
        result = self.classify_gender(new_file_path_speech_only)
        audio_info["duration_before"] = duration
        duration = librosa.get_duration(filename=new_file_path_speech_only)
        audio_info["duration_after"] = duration
        audio_info["new_file_path"] = audio_path
        audio_info["result"] = result
        os.remove(new_file_path_channel_only)
        os.remove(new_file_path_speech_only)

        return audio_info


celery = Celery(
    "workers",
    broker=os.getenv("AMQP_URL", "amqp://guest:guest@localhost:5672//"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6380/0"),
)
celery.conf.broker_connection_retry_on_startup = True

celery.task(base=PredictTask)
