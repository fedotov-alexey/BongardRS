import os 
import pathlib
import json

from strategies import load_setup, direct, InferenceResult

def ask_model(prompt, image):
    if image.exists():
        return f"answer for image {image} and prompt {prompt}"
    return "no image there :("

def reload_model():
    pass

if __name__ == "__main__":
    # inference model
    setup = load_setup("sample_setup.json")
    results = direct(ask_model, reload_model, setup)
    results.to_json("results.json")

    results_from_json = InferenceResult.load_from_json_file("results.json")