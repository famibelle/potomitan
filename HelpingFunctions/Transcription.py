import whisper

model = whisper.load_model("large-v3")

result = model.transcribe("public/audio/segment_1fd85b7b.wav",language="ht")

print(result["text"])