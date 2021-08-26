import requests
import os
from requests_html import HTMLSession
import shutil
import random
import cv2
import glob

# Variables used to determine the prefix-url to search and the folder name in 
# which the images are going to be downloaded 
URL_Google = "https://www.google.com/search?tbm=isch&q="
URL_Musix = 'https://www.musixmatch.com'
folder_name = "butItsGI/"
tag_tree_google_img = 'body > div > c-wiz > div > div > div > div > div > div > div > span > div > div > a > div > img'

#Deletes folder if it exists to empty contents and creates a new one with all permissions
def check_directory(f_name):
    if(os.path.exists(f_name)):
        shutil.rmtree(f_name)
    os.mkdir(f_name, 0o7777)

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
def search_lyric(song, url):
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

    return url + lyric_results[selectSong(dict_lyrics)+1].find('a.title',first=True).attrs['href']

#Menu to choose top songs results and returns said selection
def selectSong(list_lyrics):
    cnt = 0
    for val in list_lyrics:
        print(f"[{cnt}] Song: {val['song']} by {val['artist']}")
        cnt+=1
    choice = int(input("Select the song: "))
    try:
        if choice >= 0 and choice < len(list_lyrics):
            return choice
        else:
            raise
    except:
        print("Invalid selection")
        selectSong(list_lyrics)

#Parses and returns the lyrics in an ordered array
def get_lyric(url):
    session = HTMLSession()
    r = session.get(url)
    print(f"Fetchign lyrics for {url}")
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

    return words

#Creation of the video using the cv2 library and exporting it in mp4 format
def create_video(folder_path, output_name):
    base_dir = os.path.realpath(folder_path)
    file_name = output_name+'.mp4'
    print(base_dir)

    file_list = glob.glob(base_dir + '/*.jpg')
    frame_array = []
    for i in file_list:
        img = cv2.imread(i)
        img=cv2.resize(img, (720,480))
        h,w,l = img.shape
        size = (w,h)

        for k in range(1):
            frame_array.append(img)
    out = cv2.VideoWriter(file_name, cv2.VideoWriter_fourcc(*'mp4v'), 2, size)
    for i in range(len(frame_array)):
        out.write(frame_array[i])
    out.release()
    print(f"Video exported to {file_name}")

def main():
    check_directory(folder_name)
    #check for internet connection
    song_name = input("Song name: ")
    lyrics_complete = get_lyric(search_lyric(song_name, URL_Musix))
    print(lyrics_complete)
    count = 1
    total_count = len(lyrics_complete)
    for word in lyrics_complete:
        print(f"[{count}/{total_count}]", end=" ")
        count+=1
        search_and_download(folder_name, URL_Google, word, tag_tree_google_img, count)
    create_video(folder_name, input("File name (without extension): "))


if __name__ == "__main__":
    main()


