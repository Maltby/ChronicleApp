# -*- coding: utf-8 -*-
try:
    import os
    import re
    import sys
    import time
    import json
    import boto3
    import select
    import urllib
    import codecs
    import zipfile
    import logging
    import psycopg2
    import requests
    import nltk.data
    import wikipedia
    import traceback
    import subprocess
    from io import BytesIO
    from boto3 import Session
    from urllib import request
    from zipfile import ZipFile
    from threading import Thread
    from contextlib import closing
    from pydub import AudioSegment
    from tempfile import gettempdir
    from bs4 import BeautifulSoup, NavigableString, Tag
    from botocore.exceptions import BotoCoreError, ClientError
except:
    print('ERROR: You need to install boto3, psycopg2, nltk, ZipFile, bs4, pydub or others.')
    sys.exit(2)

s3 = boto3.client('s3')
rds = boto3.client('rds')
polly = boto3.client('polly')

def queryTop30():
    instance = False
    response = rds.describe_db_instances(DBInstanceIdentifier='booksmain')
    db_instances = response['DBInstances']

    if len(db_instances) != 1:
        raise Exception("Hey! There's more than one instance of 'booksmain', this should not occur")

    db_instance = db_instances[0]
    status = db_instance['DBInstanceStatus']
    time.sleep(5)

    if status == 'available':
        endpoint = db_instance['Endpoint']
        host = endpoint['Address']
        print('DB instance ready with host: {0}'.format(host))

        instance = psycopg2.connect(database='booksMainDatabase', user='booksMainUser', password="hit51quasar", host=host, port='5432', connect_timeout=10)
        instance.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        print('Instance created')

        cur = instance.cursor()
        print('Cursor ready')

        cur.execute("SELECT id FROM booksmain ORDER BY listens DESC LIMIT 30;")
        results = cur.fetchall()
        cur.close()
        urlArray = createUrls(results)
        filesToRDSChapters(urlArray)

def createUrls(bookIdArray):
    # Based on url gutenberg url syntax:
    # http://aleph.gutenberg.org/1/0/2/7/10274/10274-h.zip
    # http://aleph.gutenberg.org/8/84/84-h.zip
    bookUrlArray = []
    for id in bookIdArray:
        # TODO: Take while out to do full 30
        if id[0] not in [1342, 11, 84, 2542, 1661, 1952, 5200, 345, 98, 1232, 3207, 2701, 76, 2591, 2701, 3207, 16328, 844, 74, 41, 10897, 30254, 2600]:
            url = "http://aleph.gutenberg.org/"
            urlEnding = "-h.zip"
            idInt = id[0]
            indexableId = str(idInt)
            idLength = len(indexableId)
            indexCount = 0
            for index in range(idLength):
                if indexCount == idLength - 1:
                    url += indexableId + '/' + indexableId + urlEnding
                    bookInfoDict = {}
                    bookInfoDict["Id"] = indexableId
                    bookInfoDict["Url"] = url
                    bookUrlArray.append(bookInfoDict)
                    break
                character = indexableId[indexCount]
                url += character + '/'
                indexCount += 1
    return bookUrlArray

def filesToRDSChapters(bookInfoArray):
    for bookInfo in bookInfoArray:
        print('beginning work on %s' % bookInfo["Id"])
        bookId = bookInfo["Id"]
        bookUrl = bookInfo["Url"]

        # Download and open zip file
        bytes = urllib.request.urlopen(bookUrl)
        with ZipFile(BytesIO(bytes.read())) as zip:
            htmlFile = (zip.namelist()[0])
            html = zip.read(htmlFile)
            bookAllInfoArray = htmlToChapterizedDict(html, 'h2')
            # Ensure chapter headers were labelled with 'h2', else attempt with 'h3', and finally try 'h1'
            if bookAllInfoArray[1] == {}:
                bookAllInfoArray = htmlToChapterizedDict(html, 'h3')
            if bookAllInfoArray[1] == {}:
                bookAllInfoArray = htmlToChapterizedDict(html, 'h1')
            bookTitle = bookAllInfoArray[0]
            htmlDict = bookAllInfoArray[1]

            # Placeholder for rds info
            booksS3LocDict = {}
            for key, value in htmlDict.items():
                while True:
                    # Convert to mp3 and upload chapter to s3
                    title = " ".join(value['Title'].split())
                    # speaker() will create audio files and upload each chapter, returning each chapter's audio file location in S3, in a dictionary
                    s3Location = speaker(value['Text'], title, 'mp3', "Joanna", bookId)
                    if s3Location == None:
                        print('s3Location returned None, sleeping for 20 sec and retrying')
                        time.sleep(20)
                        continue
                    # booksS3LocDict[value['Title']] = s3Location
                    booksS3LocDict[key] = {"Title":title, "s3Location":s3Location}
                    break
                    # booksS3LocDict[title] = s3Location
            
            bookCoverLocation = getBookCover(bookId, bookTitle)
            # Upload chapter mp3 locations to rds
            updateS3Location(bookId, booksS3LocDict, bookCoverLocation)
            # Grab book cover image, upload to rds, update location

def htmlToChapterizedDict(htmlFile, headerString):
    # f=codecs.open("/Users/theMaltby/Desktop/10095-h.htm", 'r')
    # header input is string equal to 'h2' or other
    soup = BeautifulSoup(htmlFile, 'html.parser')

    dict = {}
    chapterCount = 0

    titleHeader = soup.find('h1')
    if titleHeader != None:
        bookTitle = " ".join(titleHeader.text.split())

    for header in soup.find_all(headerString):
        chapterText = []
        chapterCount += 1
        nextNode = header
        while True:
            if header.text == 'NOTES':
                break
            nextNode = nextNode.nextSibling
            if nextNode is None:
                chapterTextString = ' '.join(chapterText)
                dict[chapterCount] = {'Title':header.text,'Text':chapterTextString}
                # dict[header.text] = chapterTextString
                break
            if isinstance(nextNode, NavigableString):
                continue
            if isinstance(nextNode, Tag):
                if nextNode.name == "a":
                    linkText = nextNode.get_text()
                    print(linkText)
                    if linkText == "Contents":
                        chapterTextString = ' '.join(chapterText)
                        title = " ".join(header.text.split())
                        dict[chapterCount] = {'Title':title,'Text':chapterTextString}
                        break
                    continue
                elif nextNode.name == headerString:
                    nextNodeTitle = nextNode.get_text()
                    if nextNodeTitle == 'NOTES':
                        break
                    chapterTextString = ' '.join(chapterText)
                    title = " ".join(header.text.split())
                    dict[chapterCount] = {'Title':title,'Text':chapterTextString}
                    break
                # text = (nextNode.get_text())
                text = (nextNode.get_text(strip=True).strip())
                text = text.replace("\t", " ").replace("\r", " ").replace("\n", " ")
                text = " ".join(text.split())
                chapterText.append(text)
    try:
        bookMainInfoArray = [bookTitle, dict]
        return bookMainInfoArray
    except NameError:
        bookMainInfoArray = ["Title", dict]
        return bookMainInfoArray
    else:
        bookMainInfoArray = ["Title", dict]
        return bookMainInfoArray

# Create transcribed mp3 file
def speaker(chapterText, chapterTitle, outputFormat, voiceID, bookId):
    # Polly has a max character length of 1500
    # If body text is greater than 1500, break into chunks
    if len(chapterText) > 1500:
        try:
            # Tokenize text to be broken into senteces
            print('{0}.txt contains {1} characters'.format(bookId, len(chapterText)))
            tokenizedText = nltk.sent_tokenize(chapterText)
            print('{0} has been tokenized into {1} senteces'.format(bookId, len(tokenizedText)))

            # # Ensure no single sentence is greater than 1500 characters
            # ensuredTokenizedText = checkForSentencesOver1500(tokenizedText)
            # finalText = checkForSentencesOver1500(ensuredTokenizedText)
            # managableSections = breakChunksTo1500Chars(finalText)
            
            # Ensure no single sentence is greater than 1500 characters
            ensuredTokenizedText = checkForSentencesOver1500(tokenizedText)
            # Break text into managable sizes, preserving sentences
            managableSections = breakChunksTo1500Chars(ensuredTokenizedText)


            print('{0}: Managable sections: {1}'.format(bookId, len(managableSections)))
            sectionCount = 0
            sectionFiles = []
            print('Beginning {0} speech requests'.format(len(managableSections)))
            for i in managableSections:
                while True:
                    sectionCount += 1
                    try:
                        response = polly.synthesize_speech(Text=i, OutputFormat=outputFormat, VoiceId=voiceID)
                    except (BotoCoreError, ClientError) as error:
                        # The service returned an error, exit gracefully
                        print('Polly returned an error, exit gracefully')
                        print(error)
                        sys.exit(-1)

                    # Access the audio stream from the response
                    if "AudioStream" in response:
                        # Note: Closing the stream is important as the service throttles on the
                        # number of parallel connections. Here we are using contextlib.closing to
                        # ensure the close method of the stream object will be called automatically
                        # at the end of the with statement's scope.
                        with closing(response["AudioStream"]) as stream:
                            output = os.path.join(gettempdir(), "%s.mp3" % sectionCount)
                            print('Received response {0} of {1}'.format(sectionCount, len(managableSections)))
                            try:
                                # Open a file for writing the output as a binary stream
                                with open(output, "wb") as file:
                                    file.write(stream.read())
                            except IOError as error:
                                # Could not write to file, exit gracefully
                                print(error)
                                # sys.exit(-1)
                                print("Failed to convert section, sleeping for 20sec")
                                time.sleep(20)
                                continue
                            # Append audio to list of files, to be concatenated later
                            sectionFiles.append(output)
                            break
                    else:
                        # The response didn't contain audio data, exit gracefully
                        print("Could not stream audio")
                        # sys.exit(-1)
                        print("Failed to convert section, sleeping for 20sec")
                        time.sleep(20)
                        continue

            # Concatenate all audio files into one.
            print('All audio files received')
            fullAudio = concatenate_mp3_files(sectionFiles, bookId)
            print('All files concatenated')
            audioLocation = uploadMP3toS3(fullAudio, bookId, chapterTitle)
            print('Successful upload')
            return audioLocation
        except Exception as e:
            print('Error preparing text:')
            logging.error(traceback.format_exc())
            return
        # Logs the error appropriately. 
    else:
        for attempt in range(10):
            try:
                # Request speech synthesis
                response = polly.synthesize_speech(Text=chapterText, OutputFormat=outputFormat, VoiceId=voiceID)
            except (BotoCoreError, ClientError) as error:
                # The service returned an error, exit gracefully
                print(error)
                sys.exit(-1)

            # Access the audio stream from the response
            if "AudioStream" in response:
                # Note: Closing the stream is important as the service throttles on the
                # number of parallel connections. Here we are using contextlib.closing to
                # ensure the close method of the stream object will be called automatically
                # at the end of the with statement's scope.
                with closing(response["AudioStream"]) as stream:
                    output = os.path.join(gettempdir(), "speech.mp3")

                    try:
                        # Open a file for writing the output as a binary stream
                        with open(output, "wb") as file:
                            file.write(stream.read())
                    except IOError as error:
                        # Could not write to file, exit gracefully
                        print(error)
                        sys.exit(-1)
                    print('Recieved audio')
                    audioLocation = uploadMP3toS3(output, bookId, chapterTitle)
                    print('Successful upload')
                    return audioLocation

            else:
                # The response didn't contain audio data, exit gracefully
                print("Could not stream audio")
                # sys.exit(-1)
                return
        else:
            print('%i failed, move on to next book' % bookId)
            return

def checkForSentencesOver1500(tokenizedText):
    indexesOfSentencesOver1500 = []
    for chunk in tokenizedText:
        if len(chunk) > 1500:
            index = tokenizedText.index(chunk)
            indexesOfSentencesOver1500.append(index)
        else:
            continue
    
    if indexesOfSentencesOver1500 != []:
        for sentence in indexesOfSentencesOver1500:
            # Poems may contain run-on sentences split up by line breaks, attempt breaking into lines before words.
            sentenceSplit = tokenizedText[sentence].split('\n')
            for piece in sentenceSplit:
                if len(piece) > 1500:
                    words = nltk.word_tokenize(piece)
                    piecesUnder1500 = breakChunksTo1500Chars(words)
                    index = sentenceSplit.index(piece)
                    # TODO: What is this syntax doing?
                    sentenceSplit[index:index+1] = piecesUnder1500
                else:
                     continue
            # lst[i:i+1] = 'b1', 'b2', 'b3'
            # TODO: What is this syntax doing?
            tokenizedText[sentence:sentence+1] = sentenceSplit

    return(tokenizedText)

def breakChunksTo1500Chars(tokenized_text):
    # Add check to see if tokenized_text[0] changes or not, if not, catch tokenized_text and continue
    # Handle single strings greater than 1500 characters
    start = time.time()
    moreText = True
    # Updated string value to be appended to finalArray if length does not exceed 1500 chars
    updatedString = ''
    # Hold onto previous string, in case adding another sectence to updatedString pushes the length over 1500 chars
    holdPreviousString = ''
    finalArray = []
    print('len(tokenized_text): {0}'.format(len(tokenized_text)))
    while moreText:
        # lenOfPreviousLoop = len(tokenized_text)
        if not tokenized_text:
            # Final string
            if updatedString != '':
                finalArray.append(updatedString)
                updatedString = ''
            else:
                print('Text array complete.')
                moreText = False
                end = time.time()
                print('breakChunksTo1500Chars, time elapsed: ' + str(end - start))
                return finalArray
        else:
            # More strings to come
            updatedString = updatedString + " " + tokenized_text[0]
            if len(updatedString) <= 1500:
                tokenized_text.pop(0)
                holdPreviousString = updatedString
            elif len(updatedString) > 1500 and holdPreviousString == '':
                finalArray.append(tokenized_text[0])
                tokenized_text.pop(0)
            else:
                finalArray.append(holdPreviousString)
                holdPreviousString = ''
                updatedString = ''

def concatenate_mp3_files(sectionFiles, bookId):
    print('len(sectionFiles): {0}'.format(len(sectionFiles)))
    combined = AudioSegment.empty()
    count = 0 
    for audioFile in sectionFiles:
        try:
            count += 1
            audio = AudioSegment.from_file(audioFile, format="mp3")
            combined = combined + audio
            print('{0} files combined of {1}'.format(count, len(sectionFiles)))
        except:
            print('error with file combination')
    # Create temp space and return file
    print('Creating temp space')
    output = os.path.join(gettempdir(), "{0}.mp3".format(bookId))
    print('Exporting combined file to {0}.mp3'.format(bookId))
    combined.export(output, format="mp3")
    print('File combined, returning...')
    return output

def getBookCover(bookId, bookTitle):
    wikiPageResults = wikipedia.search('%s book' % bookTitle, results=1)
    if wikiPageResults != []:
        wikiPageName = wikiPageResults[0]

        wikiPage = wikipedia.page(wikiPageName)
        bookCover = wikiPage.images[0]
        fileTitleString = "_".join(bookTitle.split())

        output = os.path.join(gettempdir(), "%s.jpg" % fileTitleString)
        imageData = urllib.request.urlretrieve(bookCover, output)
        bookCoverLocation = uploadBookCoverToS3(output, bookId)
        return bookCoverLocation
    return

def uploadMP3toS3(output, bookId, chapterTitle):
    print('Attempting upload')
    chapterTitle = "".join(chapterTitle.split())
    bookIdAndChapterTitle = '{0}{1}'.format(bookId, chapterTitle)
    with open(output, 'rb') as audioData:
        print('Audio file opened.')
        s3.upload_fileobj(audioData, 'books-to-mp3', '%s.mp3' % bookIdAndChapterTitle)
    # with open(docPath, 'rb') as textData:
    #     print('Text file opened.')
    #     s3.upload_fileobj(textData, 'books-text', '%s.txt' % bookId) 
    print('Mp3 uploaded for: {0}'.format(bookIdAndChapterTitle))
    audioLocation = "{0}.mp3".format(bookIdAndChapterTitle)
    return audioLocation

def uploadBookCoverToS3(output, bookId):
    print('Attempting upload of book cover')
    s3FileTitle = str(bookId)
    with open(output, 'rb') as imageData:
        print('Audio file opened.')
        s3.upload_fileobj(imageData, 'book-cover-image', '%s.jpg' % s3FileTitle) 
    print('Jpg uploaded for: {0}'.format(s3FileTitle))
    jpgLocation = "{0}.jpg".format(s3FileTitle)
    return jpgLocation

def updateS3Location(bookId, booksS3LocDict, bookCoverLocation):
    instance = False
    response = rds.describe_db_instances(DBInstanceIdentifier='booksmain')
    db_instances = response['DBInstances']

    if len(db_instances) != 1:
        raise Exception("Hey! There's more than one instance of 'booksmain', this should not occur.")

    db_instance = db_instances[0]
    status = db_instance['DBInstanceStatus']
    time.sleep(5)

    if status == 'available':
        endpoint = db_instance['Endpoint']
        host = endpoint['Address']
        print('DB instance ready with host: {0}'.format(host))

        instance = psycopg2.connect(database='booksMainDatabase', user='booksMainUser', password="hit51quasar", host=host, port='5432', connect_timeout=10)
        instance.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        print('Instance created')

        cur = instance.cursor()
        print('Cursor ready')
        # Create loop for all incoming requests, therefore same instance can be used multiple times
        print('Updating RDS locations for: {0}'.format(bookId))

        booksLocJSON = json.dumps(booksS3LocDict)
        cur.execute("UPDATE booksmain SET s3audioLocation = '{0}'::json WHERE id = '{1}';".format(booksLocJSON, bookId))
        cur.execute("UPDATE booksmain SET available = $${0}$$ WHERE id = '{1}';".format('t', bookId))
        if bookCoverLocation != None:
            cur.execute("UPDATE booksmain SET s3bookCoverLocation = '{0}' WHERE id = '{1}';".format(bookCoverLocation, bookId))

        print('Committing locations to rds...')
        instance.commit()
        cur.close()
        print('Updated s3 locations, book is available')

queryTop30()







# # -*- coding: utf-8 -*-
# try:
#     import os
#     import re
#     import sys
#     import time
#     import json
#     import boto3
#     import select
#     import urllib
#     import codecs
#     import zipfile
#     import logging
#     import psycopg2
#     import requests
#     import nltk.data
#     import wikipedia
#     import traceback
#     import subprocess
#     from io import BytesIO
#     from boto3 import Session
#     from urllib import request
#     from zipfile import ZipFile
#     from threading import Thread
#     from contextlib import closing
#     from pydub import AudioSegment
#     from tempfile import gettempdir
#     from bs4 import BeautifulSoup, NavigableString, Tag
#     from botocore.exceptions import BotoCoreError, ClientError
# except:
#     print('ERROR: You need to install boto3, psycopg2, nltk, ZipFile, bs4, pydub or others.')
#     sys.exit(2)
# # Query ID of top 25 books

# # Download all books

# # Iterate through array of book zips, opening file and parsing to text and chapters dict

# s3 = boto3.client('s3')
# rds = boto3.client('rds')
# polly = boto3.client('polly')

# # htmlDict: 
# # {1: {'Text': "The Twilight of the...aid NOTES", 'Title': 'CONTENTS'}, 2: {'Text': ...}
# def queryTop30():
#     instance = False
#     response = rds.describe_db_instances(DBInstanceIdentifier='booksmain')
#     db_instances = response['DBInstances']

#     if len(db_instances) != 1:
#         raise Exception("Hey! There's more than one instance of 'booksmain', this should not occur.")

#     db_instance = db_instances[0]
#     status = db_instance['DBInstanceStatus']
#     time.sleep(5)

#     if status == 'available':
#         endpoint = db_instance['Endpoint']
#         host = endpoint['Address']
#         print('DB instance ready with host: {0}'.format(host))

#         instance = psycopg2.connect(database='booksMainDatabase', user='booksMainUser', password="hit51quasar", host=host, port='5432', connect_timeout=10)
#         instance.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
#         print('Instance created')

#         cur = instance.cursor()
#         print('Cursor ready')

#         cur.execute("SELECT id FROM booksmain ORDER BY listens DESC LIMIT 30;")
#         results = cur.fetchall()
#         urlArray = createUrls(results)
#         filesToRDSChapters(urlArray)

# def createUrls(bookIdArray):
#     # Based on url gutenberg url syntax:
#     # http://aleph.gutenberg.org/1/0/2/7/10274/10274-h.zip
#     # http://aleph.gutenberg.org/8/84/84-h.zip
#     bookUrlArray = []
#     for id in bookIdArray:
#         url = "http://aleph.gutenberg.org/"
#         urlEnding = "-h.zip"
#         idInt = id[0]
#         indexableId = str(idInt)
#         idLength = len(indexableId)
#         indexCount = 0
#         for index in range(idLength):
#             if indexCount == idLength - 1:
#                 url += indexableId + '/' + indexableId + urlEnding
#                 bookInfoDict = {}
#                 bookInfoDict["Id"] = indexableId
#                 bookInfoDict["Url"] = url
#                 bookUrlArray.append(bookInfoDict)
#                 break
#             character = indexableId[indexCount]
#             url += character + '/'
#             indexCount += 1
#     return bookUrlArray

# def filesToRDSChapters(bookInfoArray):
#     for bookInfo in bookInfoArray:
#         bookId = bookInfo["Id"]
#         bookUrl = bookInfo["Url"]

#         # Download and open zip file
#         bytes = urllib.request.urlopen(bookUrl)
#         with ZipFile(BytesIO(bytes.read())) as zip:
#             htmlFile = (zip.namelist()[0])
#             html = zip.read(htmlFile)
#             bookAllInfoArray = htmlToChapterizedDict(html, 'h2')
#             # Ensure chapter headers were labelled with 'h2', else attempt with 'h3', and finally try 'h1'
#             if bookAllInfoArray[1] == {}:
#                 bookAllInfoArray = htmlToChapterizedDict(html, 'h3')
#             if bookAllInfoArray[1] == {}:
#                 bookAllInfoArray = htmlToChapterizedDict(html, 'h1')
#             bookTitle = bookAllInfoArray[0]
#             htmlDict = bookAllInfoArray[1]
            
#             # Placeholder for rds info
#             booksS3LocDict = {}
#             for key, value in htmlDict.items():
#                 # Convert to mp3 and upload chapter to s3
#                 title = " ".join(value['Title'].split())
#                 # s3Location = speaker(value['Text'], value['Title'], 'mp3', "Joanna", bookId)
#                 s3Location = speaker(value['Text'], title, 'mp3', "Joanna", bookId)
#                 # booksS3LocDict[value['Title']] = s3Location
#                 booksS3LocDict[key] = {"Title":title, "s3Location":s3Location}
#                 # booksS3LocDict[title] = s3Location
            
#             bookCoverLocation = getBookCover(bookId, bookTitle)
#             # Upload chapter mp3 locations to rds
#             updateS3Location(bookId, booksS3LocDict, bookCoverLocation)
#             # Grab book cover image, upload to rds, update location

# def htmlToChapterizedDict(htmlFile, header):
#     # f=codecs.open("/Users/theMaltby/Desktop/10095-h.htm", 'r')
#     # header input is string equal to 'h2' or other
#     soup = BeautifulSoup(htmlFile, 'html.parser')

#     dict = {}
#     chapterCount = 0

#     titleHeader = soup.find('h1')
#     bookTitle = " ".join(titleHeader.text.split())

#     for header in soup.find_all(header):
#         chapterText = []
#         chapterCount += 1
#         nextNode = header
#         while True:
#             if header.text == 'NOTES':
#                 break
#             nextNode = nextNode.nextSibling
#             if nextNode is None:
#                 chapterTextString = ' '.join(chapterText)
#                 dict[chapterCount] = {'Title':header.text,'Text':chapterTextString}
#                 # dict[header.text] = chapterTextString
#                 break
#             if isinstance(nextNode, NavigableString):
#                 continue
#             if isinstance(nextNode, Tag):
#                 if nextNode.name == "a":
#                     linkText = nextNode.get_text()
#                     print(linkText)
#                     if linkText == "Contents":
#                         chapterTextString = ' '.join(chapterText)
#                         title = " ".join(header.text.split())
#                         dict[chapterCount] = {'Title':title,'Text':chapterTextString}
#                         break
#                     continue
#                 elif nextNode.name == header:
#                     nextNodeTitle = nextNode.get_text()
#                     if nextNodeTitle == 'NOTES':
#                         break
#                     chapterTextString = ' '.join(chapterText)
#                     title = " ".join(header.text.split())
#                     dict[chapterCount] = {'Title':title,'Text':chapterTextString}
#                     break
#                 # text = (nextNode.get_text())
#                 text = (nextNode.get_text(strip=True).strip())
#                 text = text.replace("\t", " ").replace("\r", " ").replace("\n", " ")
#                 text = " ".join(text.split())
#                 chapterText.append(text)
#     bookMainInfoArray = [bookTitle, dict]
#     return bookMainInfoArray

# # Create transcribed mp3 file
# def speaker(chapterText, chapterTitle, outputFormat, voiceID, bookId):
#     # Polly has a max character length of 1500
#     # If body text is greater than 1500, break into chunks
#     if len(chapterText) > 1500:
#         try:
#             # Tokenize text to be broken into senteces
#             print('{0}.txt contains {1} characters'.format(bookId, len(chapterText)))
#             tokenizedText = nltk.sent_tokenize(chapterText)
#             print('{0} has been tokenized into {1} senteces'.format(bookId, len(tokenizedText)))
#             # Ensure no single sentence is greater than 1500 characters
#             ensuredTokenizedText = checkForSentencesOver1500(tokenizedText)
#             # Break text into managable sizes, preserving sentences
#             managableSections = breakChunksTo1500Chars(ensuredTokenizedText)
#             print('{0}: Managable sections: {1}'.format(bookId, len(managableSections)))
#             sectionCount = 0
#             sectionFiles = []
#             print('Beginning {0} speech requests'.format(len(managableSections)))
#             for i in managableSections:
#                 sectionCount += 1
#                 try:
#                     response = polly.synthesize_speech(Text=i, OutputFormat=outputFormat, VoiceId=voiceID)
#                 except (BotoCoreError, ClientError) as error:
#                     # The service returned an error, exit gracefully
#                     print(error)
#                     sys.exit(-1)

#                 # Access the audio stream from the response
#                 if "AudioStream" in response:
#                     # Note: Closing the stream is important as the service throttles on the
#                     # number of parallel connections. Here we are using contextlib.closing to
#                     # ensure the close method of the stream object will be called automatically
#                     # at the end of the with statement's scope.
#                     with closing(response["AudioStream"]) as stream:
#                         output = os.path.join(gettempdir(), "%s.mp3" % sectionCount)
#                         print('Received response {0} of {1}'.format(sectionCount, len(managableSections)))
#                         try:
#                             # Open a file for writing the output as a binary stream
#                             with open(output, "wb") as file:
#                                 file.write(stream.read())
#                         except IOError as error:
#                             # Could not write to file, exit gracefully
#                             print(error)
#                             sys.exit(-1)
#                         # Append audio to list of files, to be concatenated later
#                         sectionFiles.append(output)
#                 else:
#                     # The response didn't contain audio data, exit gracefully
#                     print("Could not stream audio")
#                     sys.exit(-1)
#             # Concatenate all audio files into one.
#             print('All audio files received')
#             fullAudio = concatenate_mp3_files(sectionFiles, bookId)
#             print('All files concatenated')
#             audioLocation = uploadMP3toS3(fullAudio, bookId, chapterTitle)
#             print('Successful upload')
#             return audioLocation
#         except Exception as e:
#             print('Error preparing text:')
#             logging.error(traceback.format_exc())
#         # Logs the error appropriately. 
#     else:
#         try:
#             # Request speech synthesis
#             response = polly.synthesize_speech(Text=chapterText, OutputFormat=outputFormat, VoiceId=voiceID)
#         except (BotoCoreError, ClientError) as error:
#             # The service returned an error, exit gracefully
#             print(error)
#             sys.exit(-1)

#         # Access the audio stream from the response
#         if "AudioStream" in response:
#             # Note: Closing the stream is important as the service throttles on the
#             # number of parallel connections. Here we are using contextlib.closing to
#             # ensure the close method of the stream object will be called automatically
#             # at the end of the with statement's scope.
#             with closing(response["AudioStream"]) as stream:
#                 output = os.path.join(gettempdir(), "speech.mp3")

#                 try:
#                     # Open a file for writing the output as a binary stream
#                     with open(output, "wb") as file:
#                         file.write(stream.read())
#                 except IOError as error:
#                     # Could not write to file, exit gracefully
#                     print(error)
#                     sys.exit(-1)
#                 print('Recieved audio')
#                 audioLocation = uploadMP3toS3(output, bookId, chapterTitle)
#                 print('Successful upload')
#                 return audioLocation

#         else:
#             # The response didn't contain audio data, exit gracefully
#             print("Could not stream audio")
#             sys.exit(-1)

# def checkForSentencesOver1500(tokenizedText):
#     indexesOfSentencesOver1500 = []
#     for chunk in tokenizedText:
#         if len(chunk) > 1500:
#             index = tokenizedText.index(chunk)
#             indexesOfSentencesOver1500.append(index)
#         else:
#             continue
    
#     if indexesOfSentencesOver1500 != []:
#         for sentence in indexesOfSentencesOver1500:
#             # Poems may contain run-on sentences split up by line breaks, attempt breaking into lines before words.
#             sentenceSplit = tokenizedText[sentence].split('\n')
#             for piece in sentenceSplit:
#                 if len(piece) > 1500:
#                     words = nltk.word_tokenize(piece)
#                     piecesUnder1500 = breakChunksTo1500Chars(words)
#                     index = sentenceSplit.index(piece)
#                     # TODO: What is this syntax doing?
#                     sentenceSplit[index:index+1] = piecesUnder1500
#                 else:
#                      continue
#             # lst[i:i+1] = 'b1', 'b2', 'b3'
#             # TODO: What is this syntax doing?
#             tokenizedText[sentence:sentence+1] = sentenceSplit

#     return(tokenizedText)

# def breakChunksTo1500Chars(tokenized_text):
#     # Add check to see if tokenized_text[0] changes or not, if not, catch tokenized_text and continue
#     # Handle single strings greater than 1500 characters
#     start = time.time()
#     moreText = True
#     # Updated string value to be appended to finalArray if length does not exceed 1500 chars
#     updatedString = ''
#     # Hold onto previous string, in case adding another sectence to updatedString pushes the length over 1500 chars
#     holdPreviousString = ''
#     finalArray = []
#     while moreText:
#         # lenOfPreviousLoop = len(tokenized_text)
#         print('len(tokenized_text): {0}'.format(len(tokenized_text)))
#         if not tokenized_text:
#             # Final string
#             if updatedString != '':
#                 finalArray.append(updatedString)
#                 updatedString = ''
#             else:
#                 print('Text array complete.')
#                 moreText = False
#                 end = time.time()
#                 print('breakChunksTo1500Chars, time elapsed: ' + str(end - start))
#                 return finalArray
#         else:
#             # More strings to come
#             updatedString = updatedString + " " + tokenized_text[0]
#             if len(updatedString) < 1500:
#                 tokenized_text.pop(0)
#                 # lenOfPreviousLoop = len(tokenized_text)
#                 holdPreviousString = updatedString
#             elif len(updatedString) > 1500 and holdPreviousString == '':
#                 # This should never occur
#                 print('ERROR: Input string is greater than 1500 characters!')
#                 tokenized_text.pop(0)
#             else:
#                 finalArray.append(holdPreviousString)
#                 holdPreviousString = ''
#                 updatedString = ''

# def concatenate_mp3_files(sectionFiles, bookId):
#     print('len(sectionFiles): {0}'.format(len(sectionFiles)))
#     combined = AudioSegment.empty()
#     count = 0
    
#     for audioFile in sectionFiles:
#         try:
#             count += 1
#             audio = AudioSegment.from_file(audioFile, format="mp3")
#             combined = combined + audio
#             print('{0} files combined of {1}'.format(count, len(sectionFiles)))
#         except:
#             print('error with file combination')
#     # Create temp space and return file
#     print('Creating temp space')
#     output = os.path.join(gettempdir(), "{0}.mp3".format(bookId))
#     print('Exporting combined file to {0}.mp3'.format(bookId))
#     combined.export(output, format="mp3")
#     print('File combined, returning...')
#     return output

# def getBookCover(bookId, bookTitle):
#     wikiPageResults = wikipedia.search('%s book' % bookTitle, results=1)
#     if wikiPageResults != [] {
#         wikiPageName = wikiPageResults[0]

#         wikiPage = wikipedia.page(wikiPageName)
#         bookCover = wikiPage.images[0]
#         fileTitleString = "_".join(bookTitle.split())
        
#         output = os.path.join(gettempdir(), "%s.jpg" % fileTitleString)
#         imageData = urllib.request.urlretrieve(bookCover, output)
#         bookCoverLocation = uploadBookCoverToS3(output, bookId)
#         return bookCoverLocation
#     } return None

# def uploadMP3toS3(output, bookId, chapterTitle):
#     print('Attempting upload')
#     chapterTitle = "".join(chapterTitle.split())
#     bookIdAndChapterTitle = '{0}{1}'.format(bookId, chapterTitle)
#     with open(output, 'rb') as audioData:
#         print('Audio file opened.')
#         s3.upload_fileobj(audioData, 'books-to-mp3', '%s.mp3' % bookIdAndChapterTitle)
#     # with open(docPath, 'rb') as textData:
#     #     print('Text file opened.')
#     #     s3.upload_fileobj(textData, 'books-text', '%s.txt' % bookId) 
#     print('Mp3 uploaded for: {0}'.format(bookIdAndChapterTitle))
#     audioLocation = "{0}.mp3".format(bookIdAndChapterTitle)
#     return audioLocation

# def uploadBookCoverToS3(output, bookId):
#     print('Attempting upload')
#     s3FileTitle = str(bookId)
#     with open(output, 'rb') as imageData:
#         print('Audio file opened.')
#         s3.upload_fileobj(imageData, 'book-cover-image', '%s.jpg' % s3FileTitle) 
#     print('Mp3 uploaded for: {0}'.format(s3FileTitle))
#     mp3Location = "{0}.mp3".format(s3FileTitle)
#     return mp3Location

# def updateS3Location(bookId, booksS3LocDict, bookCoverLocation):
#     instance = False
#     response = rds.describe_db_instances(DBInstanceIdentifier='booksmain')
#     db_instances = response['DBInstances']

#     if len(db_instances) != 1:
#         raise Exception("Hey! There's more than one instance of 'booksmain', this should not occur.")

#     db_instance = db_instances[0]
#     status = db_instance['DBInstanceStatus']
#     time.sleep(5)

#     if status == 'available':
#         endpoint = db_instance['Endpoint']
#         host = endpoint['Address']
#         print('DB instance ready with host: {0}'.format(host))

#         instance = psycopg2.connect(database='booksMainDatabase', user='booksMainUser', password="hit51quasar", host=host, port='5432', connect_timeout=10)
#         instance.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
#         print('Instance created')

#         cur = instance.cursor()
#         print('Cursor ready')
#         # Create loop for all incoming requests, therefore same instance can be used multiple times
#         print('Updating RDS locations for: {0}'.format(bookId))

#         booksLocJSON = json.dumps(booksS3LocDict)
#         cur.execute("UPDATE booksmain SET s3audioLocation = '{0}'::json WHERE id = '{1}';".format(booksLocJSON, bookId))
#         cur.execute("UPDATE booksmain SET available = $${0}$$ WHERE id = '{1}';".format('t', bookId))
#         if bookCoverLocation != None {
#             cur.execute("UPDATE booksmain SET s3bookCoverLocation = '{0}' WHERE id = '{1}';".format(bookCoverLocation, bookId))
#         }

#         print('Committing locations to rds...')
#         instance.commit()
#         print('Updated s3 locations, book is available')

# queryTop30()