# What is this project
This is a way to visualize how similar different albums are based off tags that users have put on them. Somewhat inspired by Obsidian's node-graph thing.

# Data Used
Through Last.fm API, I got album level tags such as genre tags, and also album metadata. 

I had to do some data cleaning for some tags that didn't fit the project such as "seen live"

Also used MusicBrainz for the year data, sincethe Last.fm data for year was unreliable.

So far I have only extracted 250 albums.

# Methods Used

## Feature Construction
- Made a data matrix where rows were each album x ever tag. Each row was normalized so that the top tag for that row was 100.
- for each tag, a weighting scheme was used so that rare and less frequently used tags were weighted higher.
  - this was done by multipling the term frequency and the inverse document frequency (these are global attributes across all the data)
  - generic terms like "rock" or "pop" were penalized

## Computing Similarity Between Genres
- Cosine similarity, just a dot product normalized
- Weighted Jaccard per pair

## Year Similarity 
- Instead of just using distance, which bigger the difference means less similar for a year, I used a Gaussian kernel. This is because the cosine similarity and wieghted jaccard pair is the opposite where bigger the score the more similar.
-  Also, Gaussian kernel has a parameter that cobntrols how fast similarity decays with time.

## Total Similarity
- Is just a combination of the genre similarity and the year similarity.

## Results



# Steps
1. **Data download from Last.fm and MusicBrains**
2. Create a virtual environment and install dependencies through *python -m venv .venv .venv\Scripts\activate pip install -r requirements.txt*
3. Run python run.py, should take a few minutes first time
4. Serve the frontend with cd frontend python -m http.server









