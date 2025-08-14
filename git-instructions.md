# Push TradesCompass Pro to GitHub

Follow these steps to push your project to GitHub:

## 1. Open the Shell Terminal

Click on the "Shell" tab in your Replit workspace.

## 2. Configure Git (if not already done)

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

## 3. Initialize Git Repository

```bash
git init
```

## 4. Add Your GitHub Remote

Replace `yourusername` and `your-repo-name` with your actual GitHub username and repository name:

```bash
git remote add origin https://github.com/yourusername/your-repo-name.git
```

Or if using SSH:
```bash
git remote add origin git@github.com:yourusername/your-repo-name.git
```

## 5. Add All Files

```bash
git add .
```

## 6. Create Initial Commit

```bash
git commit -m "Initial commit: TradesCompass Pro - AI-powered trades recruitment platform"
```

## 7. Push to GitHub

```bash
git push -u origin main
```

If your default branch is `master`:
```bash
git push -u origin master
```

## 8. Enter GitHub Credentials

When prompted:
- **Username**: Your GitHub username
- **Password**: Your GitHub Personal Access Token (not your password!)

### How to Create a GitHub Personal Access Token:
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Give it a name like "Replit Push"
4. Select scopes: `repo` (full control of private repositories)
5. Generate and copy the token
6. Use this token as your password when pushing

## Alternative: Using Replit's GitHub Integration

1. Click the "Git" icon in the left sidebar
2. Click "Connect to GitHub"
3. Authorize Replit to access your GitHub
4. Select your repository
5. Click "Pull" then "Push" to sync changes

## Files to Push

Your repository will include:
- ✅ README.md - Complete project documentation
- ✅ All Python source files (routes.py, models.py, etc.)
- ✅ Configuration files (requirements.txt, etc.)
- ✅ Templates and static assets
- ✅ Service modules

## After Pushing

Your repository will be available at:
```
https://github.com/yourusername/your-repo-name
```

The README will be displayed on the main page with all documentation!