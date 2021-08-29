import requests
import os
import youtube_dl
from requests_html import HTMLSession
import shutil
import random
import cv2
import glob
import ffmpeg
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import gc

# Variables used to determine the prefix-url to search and the folder name in 
# which the images are going to be downloaded 
URL_Google = "https://www.google.com/search?tbm=isch&q="
URL_Musix = 'https://www.musixmatch.com'
URL_Youtube_Google = 'https://www.google.com/search?q='
folder_name = "butItsGI/"
keyword_out_file = "Full"
tag_tree_google_img = 'body > div > c-wiz > div > div > div > div > div > div > div > span > div > div > a > div > img'

#Options for audio download, change 'outmpl' if you want to change the path or name of output file
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl' : 'audio.wav'
}

#Deletes folder if it exists to empty contents and creates a new one with all permissions
def check_files(f_name, download_name, video_name, final_vid_name):
    if(os.path.exists(f_name)):
        shutil.rmtree(f_name)
    os.mkdir(f_name, 0o7777)

    if(os.path.exists(download_name)):
        os.remove(download_name)
    if(os.path.exists(video_name)):
        os.remove(video_name)
    if(os.path.exists(final_vid_name)):
        os.remove(final_vid_name)

#Searched and downloades the word passed and saves it as IMG_XXXX.jpg
def search_and_download(location, url, word, tags, cnt_img):
    word = word.lower()
    #0:04d can be changed if the word array is greater than 9999 words (hopefully not)
    location = os.path.join(location, "IMG_{0:04d}".format(cnt_img) + ".jpg")
    url += word

    session = HTMLSession()
    r = session.get(url)
    print(f"Searching image {url}")
    images = r.html.find(tags)
    cnt = 0
    links = []
    #Since the first 20 images results are a blank pixel we get the rest of images selected
    for img in images:
        if cnt > 20:
            links.append(img.attrs['data-src'])
        else:
            cnt+=1
    
    try:
        r_img = requests.get(links[random.randint(0, len(links)-1)], stream=True)
        r_img.raw.decode_content = True 
        with open(location, 'wb') as f:
            shutil.copyfileobj(r_img.raw, f)
            #Could add image directly so it doesn't process twice but would need speech-text beforehand at 60fps (min)
    except:
        print(f"Unable to download image")
     
#Return the url for the lyrics of selected song
def search_lyric(song, url, url_yt, opts_yt):
    search_url = url+"/search/" + song
    session = HTMLSession()
    r = session.get(search_url)
    print(f"Searching lyrics {search_url}")
    lyric_results = r.html.find(".showArtist.showCoverart")
    dict_lyrics = []
    for res in lyric_results[1:]: #Starts from the second song since the first and second are the same
        text = res.text
        info = {'song' : text[:text.index('\n')], 'artist' : text[text.index('\n')+1:]}
        dict_lyrics.append(info)

    return url + lyric_results[selectSong(dict_lyrics, url_yt, opts_yt)+1].find('a.title',first=True).attrs['href']

#Searches for the song and downloads the first youtube result
def download_audio_song(search, base_url):
    url = base_url + search
    print(f'Searching audio for: {search} in {url}')
    ses = HTMLSession()
    r = ses.get(url)

    #Optional if you want to choose the music video rather than getting the highest valued, assumes entered input is correct
    link_list = []
    for link in r.html.links:
        if(link.startswith('https://www.youtube.com')):
            link_list.append(link)
    i = 0
    for link in link_list:
        print(f"[{i}] {link}")
        i+=1
    sel = int(input("Selection: "))
    return link_list[sel]

    for link in r.html.links:
        if(link.startswith('https://www.youtube.com')):
            return link
    return print(f"Unable to audio for {search}")
    

#Menu to choose top songs results, selected result is searched for its audio download and selection is returned
def selectSong(list_lyrics, url_yt, opts_yt):
    cnt = 0
    for val in list_lyrics:
        print(f"[{cnt}] Song: {val['song']} by {val['artist']}")
        cnt+=1
    choice = int(input("Select the song: "))
    if choice >= 0 and choice < len(list_lyrics):
        #Download works in mysterious ways, so don't try passing it a standalone string, it's beyond me why this happends
        #Spend about 30 minutes wondering why, if you know, let me know
        href = []
        href.append(download_audio_song(list_lyrics[choice]['song'] + " " + list_lyrics[choice]['artist'], url_yt))
        try:
            youtube_dl.YoutubeDL(opts_yt).download(href)
            
        except:
            print("Unable to download audio for song")
        return choice
            
    else:
        print("Invalid selection")
        selectSong(list_lyrics, url_yt, opts_yt)

#Parses and returns the lyrics in an ordered array
def get_lyric(url):
    session = HTMLSession()
    r = session.get(url)
    print(f"Fetching lyrics for {url}")
    lyrics = r.html.find('p.mxm-lyrics__content')
    #Could use trim to auto erase punctuation and only loop for spaces (split lines might work)
    words=[]
    for lyric in lyrics:
        word = ""
        for c in lyric.text:
            if((c != '!' or c != '.' or c != ',' or c != '\n' or c!= '?') and c != ' '):
                word+=c
            elif c == ' ':
                words.append(word)
                word = ""
    print("Lyrics succesfully fetched")
    return words

#Function for non_silent to normalize all audio 
def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)

#Processes when audio is within dB range, timestamps it and returns it along with the total song duration in ms
def non_silent(file):
    audio_segment = AudioSegment.from_file(file)
    #Normalized -20 dB has given the best results overall but feel free to try any other
    normalized_audio = match_target_amplitude(audio_segment, -20.0)
    time = len(normalized_audio)
    print("Length of audio: {} seconds".format(time/1000))
    #Change min_silence_len and silence_thresh accordingly for a more precise parse, this is roughly the best values overall
    nonsilent_data = detect_nonsilent(normalized_audio, min_silence_len=500, silence_thresh=-27, seek_step=1)
    print("Audio timestamps processed!")
    return  nonsilent_data, time

#Creation of the video using the cv2 library and exporting it in mp4 format
def create_video(folder_path, output_name, timestamps, blank, t_time):
    base_dir = os.path.realpath(folder_path)
    file_name = output_name
    print(base_dir)
    index_timestamps = 0
    counter = 0
    img_counter = 0
    file_list = glob.glob(base_dir + '/*.jpg')
    frame_array = []
    while img_counter <= len(file_list)-1 and counter < t_time:
        if(counter >= timestamps[index_timestamps][0] and counter <= timestamps[index_timestamps][1]):
            img = cv2.imread(file_list[img_counter])
            img=cv2.resize(img, (720,480))
            h,w,l = img.shape
            size = (w,h)
            times_img = 0
            img_counter+=1
            while(counter >= timestamps[index_timestamps][0] and counter <= timestamps[index_timestamps][1]) and (times_img < random.randint(2,5)):
                frame_array.append(img)
                counter+=100
                times_img+=1
            if not(counter >= timestamps[index_timestamps][0] and counter <= timestamps[index_timestamps][1]):
                if(index_timestamps < len(timestamps)-1):
                    index_timestamps+=1
        else:
            img = cv2.imread(blank)
            img=cv2.resize(img, (720,480))
            h,w,l = img.shape
            size = (w,h)
            gc.collect()
            while not(counter >= timestamps[index_timestamps][0] and counter <= timestamps[index_timestamps][1]):
                frame_array.append(img)
                counter+=100
    out = cv2.VideoWriter(file_name, cv2.VideoWriter_fourcc(*'mp4v'), 10, size)
    for i in range(len(frame_array)):
        out.write(frame_array[i])
    out.release()
    print(f"Video exported to {file_name}")

def main():
    #check for internet connection function later
    
    song_name = input("Song name: ")
    out_file = input("File name for video: ")
    out_file += ".mp4"
    video_file = keyword_out_file + out_file
    check_files(folder_name, ydl_opts['outtmpl'], out_file, video_file)

    lyrics_complete = get_lyric(search_lyric(song_name, URL_Musix, URL_Youtube_Google, ydl_opts))
    non_silent_audio_timestamps, time = non_silent(ydl_opts["outtmpl"])
    count = 1
    total_count = len(lyrics_complete)
    for word in lyrics_complete:
        print(f"[{count}/{total_count}]", end=" ")
        search_and_download(folder_name, URL_Google, word, tag_tree_google_img, count)
        count+=1
    blank_img = folder_name + "IMG_{0:04d}".format(count+1) + ".jpg"
    search_and_download(folder_name, URL_Google, "black screen", tag_tree_google_img, count+1)
    create_video(folder_name, out_file, non_silent_audio_timestamps, blank_img, time)
    
    ffmpeg.concat(ffmpeg.input(out_file), ffmpeg.input(ydl_opts["outtmpl"]), v=1,a=1).output(video_file).run()
    print(f"All processes done, video saved under {video_file}")

if __name__ == "__main__":
    main()


