# Netlify Deployment Guide

To deploy the Anti-Scam Agent UI to Netlify, follow these steps:

## Prerequisites
1. You have already deployed the backend API (e.g., to Render).
2. You have the API URL ready (e.g., `https://anti-scam-agent.onrender.com`).

## Deployment Steps

### Method 1: Drag & Drop (Easiest)
1. Go to [Netlify Drop](https://app.netlify.com/drop).
2. Drag and drop the `index.html` file into the upload area.
3. Once deployed, open the site.
4. Click on **API Settings** in the top right corner.
5. Paste your backend API URL and click **Save Settings**.

### Method 2: GitHub Integration
1. Push the `index.html` file to a GitHub repository.
2. Sign in to Netlify and click **Add new site** > **Import an existing project**.
3. Select your repository.
4. Leave the build settings empty (since it's a static HTML file).
5. Click **Deploy site**.

## Security Note
The frontend communicates directly with your backend. Ensure that your backend (Render) has the environment variables set correctly and that `api_service.py` is running with CORS enabled (which is already implemented in the current code).
