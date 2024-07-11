import os
import logging
import sys

import librosa
import numpy as np
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

    def check_operator(self, audio_title):
        file_name = ".".join(audio_title.split(".")[:-1]).split("_")[-2]
        if len(file_name) == 3 and file_name.isdigit():
            return True
        else:
            return False

    def get_customer_speech(self, file_path, audio_title):
        try:
            y, sr = librosa.load(file_path, mono=False)
            if self.check_operator(audio_title):
                client_channel = 1
            else:
                client_channel = 0
            client_speech = y[client_channel]

            # set mono channel
            if len(client_speech.shape) > 1:
                client_speech = np.mean(client_speech, axis=0)
            # normalize audio
            client_speech = librosa.util.normalize(client_speech)

            return client_speech, sr
        except Exception as e:
            logging.error("Failed to get customer speech: %s", str(e))
            raise e

    def extract_feature(self, audio_data, sample_rate, **kwargs):
        mfcc = kwargs.get("mfcc")
        chroma = kwargs.get("chroma")
        mel = kwargs.get("mel")
        contrast = kwargs.get("contrast")
        tonnetz = kwargs.get("tonnetz")
        X = audio_data
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

    def classify_gender(self, audio_data, sample_rate):
        try:
            features = self.extract_feature(audio_data, sample_rate, mel=True).reshape(
                1, -1
            )
            male_prob = self.model_gender.predict(features)[0][0]
            female_prob = 1 - male_prob
            gender = "male" if male_prob > female_prob else "female"
            result = {
                "gender": gender,
                "male_probability": f"{male_prob * 100:.2f}%",
                "female_probability": f"{female_prob * 100:.2f}%",
            }
            return result
        except LibrosaError as e:
            logging.error("Failed to extract feature: %s", str(e))
            raise e
        except Exception as e:
            logging.error("Failed to classify gender: %s", str(e))
            raise e

    def classify_speaker_gender(self, audio_path, audio_title):
        client_speech, sr = self.get_customer_speech(audio_path, audio_title)
        result = self.classify_gender(client_speech, sr)
        return result


celery = Celery(
    "workers",
    broker=os.getenv("AMQP_URL", "amqp://guest:guest@localhost:5672//"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6380/0"),
)
celery.conf.broker_connection_retry_on_startup = True

celery.task(base=PredictTask)
