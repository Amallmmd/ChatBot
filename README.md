# ShipWatch Bot

<p>
<img src="https://img.shields.io/badge/Python-239120?logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Github-181717?logo=github&logoColor=white" />
<img src="https://img.shields.io/badge/GIT-E44C30?logo=git&logoColor=white" />
<img src="https://img.shields.io/badge/prettier-1A2C34?logo=prettier&logoColor=white" />
<img src="https://img.shields.io/badge/GitHub_Actions-563D7C?logo=github-actions&logoColor=white"/>
<img src="https://img.shields.io/badge/Matplotlib-%23ffffff.svg?&logo=Matplotlib&logoColor=black">
<img src="https://img.shields.io/badge/pandas-%23150458.svg?&logo=pandas&logoColor=white">
<img src="https://img.shields.io/badge/Plotly-%233F4F75.svg?&logo=plotly&logoColor=white">
<img src="https://img.shields.io/badge/Google_Cloud-4285F4?&logo=google-cloud&logoColor=white">
</p>

![MIT License](https://img.shields.io/badge/License-MIT-lightgray.svg)
![build](https://img.shields.io/badge/Build-passing-green.svg)


### Installation and Setup 🛠️

These installation instructions assume that you have conda installed and added to your path.

*To get started with ShipWatch Bot, follow these steps:*

1. Clone the Repository: Clone this repository to your local machine using the following command:

   ```bash
   git clone <your-repo-url>
   cd <your-repo-folder>
   ```

2. Create a virtual environment (or modify an existing one).
   ```bash
   python -m venv venv
   ```
   
   #### On Windows:
   ```bash
   venv\Scripts\activate
   ```

   #### On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

3. Install all required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   - Create a `.env` file in the project root.
   - Add your Google Gemini API key:
     ```env
     GOOGLE_API_KEY=your_gemini_api_key_here
     ```

5. Start the FastAPI server:
   ```bash
   uvicorn WebApp.main:app --reload
   ```
   The app will be available at [http://localhost:8000](http://localhost:8000)

6. Open your browser and interact with ShipWatch Bot's web interface.

---

## Features 🚢
- Modern web UI for noon data entry and vessel status tracking
- Contradiction detection and chat-based resolution using Gemini 2.0
- Only allows valid vessel names and dates (no future dates)
- Data table with show/hide toggle
- FastAPI backend with in-memory storage (easy to extend)

---

This project is licensed under the [MIT License](LICENSE).


## Acknowledgements 🙌

- [Gemini 2.0](https://ai.google.dev/gemini-api/docs)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Google Generative AI](https://ai.google.dev/)
- [Bootstrap 5](https://getbootstrap.com/)
- [Agents and Open Source Contributors](https://github.com/)

---