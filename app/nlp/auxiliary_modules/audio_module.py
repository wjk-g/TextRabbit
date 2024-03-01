#from pydub import AudioSegment
#from pydub.utils import make_chunks
#import math
#import os
#
#def convert_to_mp3_and_split(file_path, output_dir, target_size_mb=15):
#    # Determine file format from the extension
#    #file_format = os.path.splitext(file_path)[1][1:]
#
#    audio = AudioSegment.from_file(file_path, format = "mp3")
#    #temp_mp3_path = os.path.splitext(file_path)[0] + '.mp3'
#    #audio.export(temp_mp3_path, format='mp3')
#
#    # Check the size of the converted file
#    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
#    print("file_size_mb: ", file_size_mb)
#
#    # Split if the file is too large
#    if file_size_mb > target_size_mb:
#        chunk_length_ms = (target_size_mb / file_size_mb) * len(audio)
#        chunks = make_chunks(audio, chunk_length_ms)
#        print("chunk_length_ms: ", chunk_length_ms)
#        print("chunks: ", chunks)
#
#        chunk_names = []
#
#        # Export the chunks
#        for i, chunk in enumerate(chunks):
#            chunk_name = os.path.join(output_dir, f"chunk_{i}.mp3")
#            chunk.export(chunk_name, format="mp3")
#            chunk_names.append(chunk_name)
#
#    return chunk_names
#
#    # Cleanup: remove the temporary MP3 file if not split
#    #if file_size_mb <= target_size_mb:
#    #    os.remove(temp_mp3_path)