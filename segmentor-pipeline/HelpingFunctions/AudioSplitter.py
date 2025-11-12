from tqdm import tqdm


from torchspleeter.command_interface import *
input_audio_file = "Mp3/audio_example.mp3"

output_directory = "Mp3"

outputfiles=split_to_parts(input_audio_file,output_directory)