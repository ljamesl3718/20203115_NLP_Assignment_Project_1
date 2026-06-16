#20203115_NLP_Assignment_02

# What to download

There are 2 options;

1. Clone the full GitHub repository.
2. Download the repository as a ZIP file and extract it.

GitHub repository:

`https://github.com/ljamesl3718/20203115_NLP_Assignment_Project_1.git`

If you download files manually, these are the required files and folders for running the prototype:

- `app.py`
- `prototype/`
- `static/`
- `sample_data/`
- `requirements.txt`

## How to run

### Option 1: Clone with Git

```powershell
git clone https://github.com/ljamesl3718/20203115_NLP_Assignment_Project_1.git
cd 20203115_NLP_Assignment_Project_1
pip install -r requirements.txt
python app.py
```

Then open:

`http://127.0.0.1:8000`

### Option 2: Download ZIP from GitHub

1. Open the GitHub repository page.
2. Click `Code`.
3. Click `Download ZIP`.
4. Extract the ZIP file.
5. Open a terminal in `output/step2_prototype`.
6. Run:

```powershell
pip install -r requirements.txt
python app.py
```

Then open:

`http://127.0.0.1:8000`

## Notes

- The app runs locally in the browser.
- `Load Sample` can be used to test the prototype quickly after the server starts.
- The upgraded prototype uses a local multilingual SentenceTransformer model for AI-based evidence matching.
- Default local model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Set `LOCAL_EMBEDDING_MODEL` to use a different sentence-transformer model.
- Set `LOCAL_EMBEDDING_LOCAL_FILES_ONLY=1` to force the app to use the cached model without contacting Hugging Face.
