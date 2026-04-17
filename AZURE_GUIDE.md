# Microsoft Azure App Registration Guide

This guide explains how to register an application in the Azure Portal to enable Microsoft & Xbox Live login for this dashboard.

## 1. Create a New App Registration

1. Log in to the [Azure Portal](https://portal.azure.com/).
2. Search for and select **"Entra ID"** (formerly Azure Active Directory).
3. In the left-hand menu, click **"App registrations"** and then **"New registration"**.
4. **Registration Details**:
   - **Name**: e.g., `Minecraft-Server-Dashboard`
   - **Supported account types**: Select **"Personal Microsoft accounts only"** (if you only want players to join) or **"Accounts in any organizational directory and personal Microsoft accounts"** (recommended for maximum compatibility).
   - **Redirect URI**: 
     - Select **"Web"** from the dropdown.
     - Enter your callback URL: `http://<your-ip>:5000/callback` (or `https://your-domain.com/callback`).
5. Click **"Register"**.

## 2. Get Application (Client) ID

1. Once registered, you will be on the **Overview** page.
2. Copy the **"Application (client) ID"**. This value goes into `MS_CLIENT_ID` in your `.env` file.

## 3. Create a Client Secret

1. In the left-hand menu, click **"Certificates & secrets"**.
2. Go to the **"Client secrets"** tab and click **"+ New client secret"**.
3. **Description**: e.g., `Dashboard-Secret`
4. **Expires**: Choose a duration (e.g., 180 days).
5. Click **"Add"**.
6. **IMPORTANT**: Copy the **"Value"** immediately. You will not be able to see it again. This value goes into `MS_CLIENT_SECRET` in your `.env` file.

## 4. Configure Authentication for Xbox Live

1. In the left-hand menu, click **"Authentication"**.
2. Ensure **"Allow public client flows"** is set to **No** (the dashboard uses a backend "Confidential Client" flow).
3. Ensure the Redirect URI you entered earlier is correct.

## 5. API Permissions (Optional but Recommended)

Note: The dashboard requests the `XboxLive.signin` scope dynamically, but you can pre-configure it:

1. Click **"API permissions"** -> **"+ Add a permission"**.
2. Search for **"Xbox Live"** (if available) or use **"Microsoft Graph"** -> **"User.Read"** (for basic profile access).
3. *Note: Most Xbox permissions are requested directly by the app during the login flow.*

## 6. Update your .env File

Replace the placeholders in your `.env` file with the values from Azure:

```env
MS_CLIENT_ID=00000000-0000-0000-0000-000000000000
MS_CLIENT_SECRET=your_secret_value_here
MS_REDIRECT_URI=http://your-ip:5000/callback
MS_AUTHORITY=https://login.microsoftonline.com/consumers
```

> [!IMPORTANT]
> **Production Note**: If you use `https` in production, ensure the `MS_REDIRECT_URI` starts with `https://`. Azure will reject authentication requests if the URI doesn't match exactly.
