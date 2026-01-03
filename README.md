# LMS Alternative
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flet](https://img.shields.io/badge/Flet-UI-green.svg)
![Google Drive API](https://img.shields.io/badge/Google%20Drive-API%20v3-yellow.svg)

## 📖 Description

**LMS Alternative** is a robust desktop application designed to streamline the academic workflow for students and educators. Built with [Flet](https://flet.dev/) (Python), it functions as a lightweight **Learning Management System (LMS)** that integrates seamless file management with essential academic tools.

By layering organizational features over **Google Drive**, this application provides a centralized dashboard where users can manage assignments, track deadlines, and organize course materials without the complexity of traditional LMS platforms. Whether you need to submit assignments, manage shared resources, or simply keep your digital workspace tidy, LMS Alternative offers a simple, efficient solution.

## 🎯 Purpose

This application serves as a **lightweight alternative to traditional Learning Management Systems (LMS)**, specifically designed to solve common student challenges:

- **📚 Centralized Assignment Management** – No more hunting through countless Google Drive links for different subjects and assignments
- **✅ To-Do List with Smart Notifications** – Track assignments with due dates and get timely reminders before and after deadlines
- **⏰ Time Tracking** – See remaining time for each assignment at a glance
- **🔗 Quick Link Access** – Organize and access all your course folders and assignment submission links in one place
- **📂 Subject-Based Organization** – Keep everything organized by subject/course for easy navigation

Perfect for students who need a simple, efficient way to manage their academic workload without the complexity of full-featured LMS platforms.

---

## ✨ Features

### 🎓 LMS Features
- **📋 Assignment To-Do List** – Create and manage assignments with due dates
- **🔔 Smart Notifications** – Get reminders before and after assignment due dates
- **⏱️ Time Remaining Tracker** – Visual countdown showing time left to complete tasks
- **📚 Subject Organization** – Organize assignments and folders by course/subject
- **🔗 Assignment Link Management** – Store and quickly access Google Drive submission folders for each assignment

### 📁 Google Drive Management
- **🔐 Google OAuth Authentication** – Secure login using your Google account
- **📁 Browse & Navigate** – Explore your Google Drive folders with an intuitive interface
- **🔍 Search** – Quickly find files and folders across your Drive
- **📂 Shared Drives Support** – Access and browse shared drives
- **🔗 Paste Drive Links** – Open folders/files directly by pasting Google Drive links
- **⭐ Favorites** – Save frequently accessed folders organized by category
- **📝 File Operations** – Create folders, upload files, rename, and delete
- **💾 Saved Links** – Keep a list of important Drive links for quick access
- **🔄 Caching** – Smart caching for improved performance and reduced API calls

---

## 📋 Prerequisites

- Python 3.8 or higher
- Google Cloud Platform project with Drive API enabled
- OAuth 2.0 credentials (`credentials.json`)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ASTRALLIBERTAD/LMS-alternative.git
cd capstone
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```
pip install flet google-auth google-auth-oauthlib google-api-python-client
```

### 4. Set Up Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. In the left sidebar, go to **APIs & Services** → **Library**.
4. Search for **Google Drive API**.
5. Click on **Google Drive API** → **Enable**.
6. Go to **APIs & Services** → **Credentials**.
7. Click **Create Credentials** → **OAuth 2.0 Client ID**.
8. If prompted, configure the OAuth consent screen:

   - Select External for testing or Internal if only for your organization.
   - Fill in App Name, User Support Email, and Developer Email.
   - Save and continue (you can skip scopes for now for basic setup).

9. Back to Create OAuth 2.0 Client ID:

   - Select Desktop App as the application type.
   - Give it a name (e.g., MLS-alternative).
   - Click Create.

10. After creating, click Download JSON.
11. Save it in your project folder, e.g., services/credentials.json.
12. In the left sidebar:
      - APIs & Services → OAuth consent screen

13. Scroll down to the section Test users.

14. Click Add users.

15. Enter the Gmail accounts that will be allowed to use your OAuth app in testing mode:
      - You can add your own Gmail.
      - You can add multiple test accounts if needed.
## 🎮 Usage

Run the application:

```bash
flet main.py
```

### First Launch

1. Click **"Login with Google"**
2. A browser window will open for Google authentication
3. Grant the requested permissions
4. You'll be redirected to the main dashboard

### Main Features

| Feature | Description |
|---------|-------------|
| **Your Folders** | Browse folders in your personal Drive |
| **Shared Drives** | Access shared/team drives |
| **Paste Links** | Open Drive links directly by pasting them |
| **Search** | Find files and folders by name |
| **New** | Create new folders or upload files |
| **Favorites** | Save folders organized by subject/category |

## 📁 Project Structure

```
capstone/
├── src/
│   ├── assets/               
│   │   ├── icon.png          # Default application icon
│   │   ├── icon_android.png  # Andriod app icon
│   │   └── splash_android.png # Android splash screen icon
│   └── services/
│   │   ├── auth_service.py   # Authentication logic
│   │   ├── drive_service.py  # Drive API operations
│   │   ├── fcm_integration.py # Firebase Cloud Messaging setup
│   │   ├── fcm_service.py    # Firebase notification logic
│   │   ├── file_preview_service.py # File thumbnail/review
│   │   └── notification_service.py # Notiication management
│   └── ui/
│   │   └── custom_control/
│   │   │   ├── __init__.py   
│   │   │   ├── custom_controls.py        # Custom UI components
│   │   │   ├── gmail_profile_menu.py     # Gmail profile dropdown
│   │   │   ├── multi_account_manager.py  # Interface for switching accounts
│   │   └── dashboard_modules/   
│   │   │   ├── __init__.py
│   │   │   ├── file_manager.py        # Logic for managing files
│   │   │   ├── folder_navigator.py    # Directory and breadcrumbs
│   │   │   ├── paste_links_manager.py # URL link management
│   │   └── todo modules/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py           # Main dashboard UI
│   │   │   ├── firebase_mobile_login.py # Mobile login
│   │   │   ├── login.py               # Login screen 
│   │   │   └── todo_view.py           # To do screen
│   └── utils/
│   │   ├── __init__.py
│   │   └── main.py           # Main application entry point
├── venv/                     # Virtual environment
├── .gitignore                # Git exclusion file
├── connect.py                # Database or network connection logic
├── LICENSE.txt               # Project licensing terms
├── lms_config.json           # LMS configuration settings
├── pyproject.toml            # Build system configuration
├── requirements.txt          # Python project dependencies
├── README.md                 # Project documentation
├── requirements.txt          # Project dependencies
├── test_firebase_connections.py # Firebase connection tests
├── test_notifications.py     # Notification system tests
└── vitural.txt               # Environment reference log
```

## 🔧 Configuration

The application stores configuration in the following files:

| File | Purpose |
|------|---------|
| `services/credentials.json` | Google OAuth credentials (required) |
| `services/token.pickle` | Authentication token (auto-generated) |
| `saved_links.json` | Saved Drive links |
| `favorites.json` | Favorite folders by category |

## 🛡️ Security

- OAuth tokens are stored locally in `token.pickle`
- Credentials never leave your device
- Add the following to `.gitignore`:
  ```
  services/credentials.json
  services/token.pickle
  ```

## 📝 Supported Google Drive Link Formats

The app supports pasting links in these formats:

- `https://drive.google.com/drive/folders/FOLDER_ID`
- `https://drive.google.com/file/d/FILE_ID`
- `https://drive.google.com/...?id=ID`

## 🤝 Contributing

We welcome contributions! Follow these steps to contribute to this project:

### 1. Fork the repository
   Click the **Fork** button at the top-right of this repository to create your own copy.
### 2. Clone your fork locally

   ```bash
   git clone https://github.com/<your-username>/LMS-alternative.git 
   cd LMS-alternative
   ```

### 3. Setup the Workspace

3.1 **Create Virtual Environment**:

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3.2 **Install Dependencies**:

```bash
pip install flet google-auth google-auth-oauthlib google-api-python-client
```

3.3 **Set Up Google Cloud Credentials**

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. In the left sidebar, go to **APIs & Services** → **Library**.
4. Search for **Google Drive API**.
5. Click on **Google Drive API** → **Enable**.
6. Go to **APIs & Services** → **Credentials**.
7. Click **Create Credentials** → **OAuth 2.0 Client ID**.
8. If prompted, configure the OAuth consent screen:

   - Select External for testing or Internal if only for your organization.
   - Fill in App Name, User Support Email, and Developer Email.
   - Save and continue (you can skip scopes for now for basic setup).

9. Back to Create OAuth 2.0 Client ID:

   - Select Desktop App as the application type.
   - Give it a name (e.g., MLS-alternative).
   - Click Create.

10. After creating, click Download JSON.
11. Save it in your project folder, e.g., services/credentials.json.
12. In the left sidebar:
      - APIs & Services → OAuth consent screen

13. Scroll down to the section Test users.

14. Click Add users.

15. Enter the Gmail accounts that will be allowed to use your OAuth app in testing mode:
      - You can add your own Gmail.
      - You can add multiple test accounts if needed.

16. Click Save.


### 4. Create a feature branch

   ```bash
   git checkout -b feature/amazing-feature
   ```
### 5. Make your changes
   Implement your feature or fix a bug.

### 6. Commit your changes

   ```bash
   git add .
   git commit -m "Add amazing feature"
   ```
### 7. Push to your branch

   ```bash
   git push origin feature/amazing-feature
   ```
### 8. Open a Pull Request (PR)
   Go to your fork on GitHub and click **Compare & Pull Request** to submit your changes to the original repository.

**Tips:** Keep branch names descriptive (`feature/...` or `fix/...`), write clear commit messages, and make sure your code is tested before submitting.


## 📄 License

This project is licensed under the MIT License. 
See [`LICENSE`](LICENSE.txt) for more information.

## 🙏 Acknowledgments

- [Flet](https://flet.dev/) – Cross-platform UI framework for Python
- [Google Drive API](https://developers.google.com/drive) – Cloud storage API
