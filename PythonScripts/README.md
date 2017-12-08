# Python scripts

Both of these are currently run manually, ahead of time, and only process a handful of the most popular books. htmlToChapterText.py will only successfully parse about 75% of books, due to the inconsistencies of the HTML files. Planning on ensuring that it can parse all books, than hosting the script on EC2, allowing users to request any of the 58,000+ books currently available from Gutenberg.

## metadataPull.py
From [andreasvc](https://gist.github.com/andreasvc/b3b4189120d84dec8857), modified to handle null metadata and push results to a postgres database.

## htmlToChapterText.py
Downloads html representations of books from Gutenberg. Books are parsed into chapters before being transcribed by AWS Polly. Transcription MP3s are uploaded to AWS S3 and postgres db is updated with locations of files.