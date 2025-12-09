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

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project 
3. Enable the **Google Drive API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client IDs**
5. Select **Desktop App** as the application type
6. Download the credentials and save as `services/credentials.json`

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
├── main.py                 # Application entry point
├── README.md               # Project Overview
├── saved_links.json        # Saved Drive links (auto-generated)
├── favorites.json          # Saved favorites (auto-generated)
├── services/
│   ├── auth_service.py     # Google OAuth authentication
│   ├── drive_service.py    # Google Drive API operations
│   ├── credentials.json    # OAuth credentials (you provide)
│   └── token.pickle        # Auth token (auto-generated)
├── ui/
│   ├── dashboard.py        # Main dashboard UI
│   ├── login.py            # Login screen
│   └── custom_control/     # Custom UI components
└── venv/                   # Virtual environment
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
   cd <repo-name>
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
3. Enable the **Google Drive API**.
4. Navigate to **Credentials** → **Create Credentials** → **OAuth 2.0 Client IDs**.
5. Select **Desktop App** as the application type.
6. Download the credentials and save the file as `services/credentials.json`.


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
Copyright © 2025 **Prince Gabrielle Jhon M. Libertad (ASTRALLIBERTAD)**  
See [`LICENSE`](LICENSE) for more information.

## 🙏 Acknowledgments

- [Flet](https://flet.dev/) – Cross-platform UI framework for Python
- [Google Drive API](https://developers.google.com/drive) – Cloud storage API
