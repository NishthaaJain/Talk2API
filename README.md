# Talk2API - User & Task Management API with Chatbot Integration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ The Wow Factor: Premium UI & Dual Themes

A modern, full-featured **FastAPI** project designed for managing users and their tasks, with a seamless integration of an AI-powered chatbot. The frontend provides an interactive, high-design user interface with support for two unique themes.

| Dark Mode (Deep Ocean/Neon) | Light Mode (Sunset/Coral) |
| :---: | :---: |
| ![Screenshot of the Chatbot in Dark Mode (Deep Ocean/Neon)](./path/to/dark_theme_screenshot.png) | ![Screenshot of the Chatbot in Light Mode (Sunset/Coral)](./path/to/light_theme_screenshot.png) |

---

## 💡 Key Features

* **Chatbot Integration:** AI assistant using OpenAI GPT to automatically call the correct API endpoints based on **natural language input**.
* **Unique Frontend:** **Stunning UI** with interactive animations, Glassmorphism, and a seamless theme toggle.
* **Dual-Theme Support:** Beautiful, contrasting **Dark (Deep Ocean)** and **Light (Sunset Coral)** themes for a better user experience.
* **User Management:** Register, update, delete, and **filter users** by username, email, or phone number.
* **Task Management:** Create, update, delete, and **filter tasks** by title, content, completion status, or assigned user.
* **Clean Code & Security:** Passwords are **hashed using bcrypt**, environment variables are protected via `.env`, ensuring a secure application.
* **CORS Enabled:** Secure cross-origin API access for frontend integration.

---

## 🛠️ Technology Stack

* **Web Framework:** **FastAPI**, Uvicorn
* **Database:** SQLAlchemy, PyMySQL
* **Authentication & Security:** Passlib (bcrypt), dotenv
* **AI/ML Integration:** **OpenAI GPT API**
* **Frontend:** HTML, **CSS Variables**, JavaScript

---

## 🚀 Installation & Setup

1.  **Clone the repository** (if running locally):
    ```bash
    git clone [https://github.com/](https://github.com/)<your-username>/<repo-name>.git
    cd <repo-name>
    ```

2.  **Create a virtual environment** and activate it:
    ```bash
    python -m venv .venv
    # Windows
    source .venv/Scripts/activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Add environment variables:**
    Create a **`.env`** file in the project root with your keys and database info. Example:

    ```
    OPEN_API_KEY=your_openai_key_here
    DB_USER=root
    DB_PASSWORD=yourpassword
    DB_HOST=localhost
    DB_NAME=yourdb
    ```

5.  **Run the application:**
    ```bash
    uvicorn app.main:app --reload
    ```
6.  **Access the project:**
    * **Frontend:** `http://127.0.0.1:8000`
    * **API documentation (Swagger UI):** `http://127.0.0.1:8000/docs`

---

## ✍️ Usage Tips

* Use the chatbot at `/chatbot_gpt/` to quickly interact with the APIs via **natural language**.
* Filter users or tasks using query parameters:
    * **Users:** `name`, `email_add`, `phone_num`
    * **Tasks:** `task_title`, `task_content`, `is_completed`, `user_id`
* Keep sensitive information like API keys and database credentials in `.env` — **never commit them**.

---

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.
