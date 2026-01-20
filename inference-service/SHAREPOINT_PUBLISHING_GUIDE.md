# SharePoint Publishing Setup Guide

**Scope**: Configuration required to enable the `sharepoint_publisher.py` module to create and publish modern .aspx pages in SharePoint Online.

---

## 1. Microsoft Entra ID (Azure AD) Configuration

The Publisher module runs as a background service using the **Client Credentials Flow**. It acts as an application identity to create pages without user interaction.

### Step 1.1: Register the Application
*(If you already created an app for Ingestion, you can reuse it, but you must add the "Write" permissions below.)*

1. **Azure Portal** > **Microsoft Entra ID** > **App registrations**.
2. **+ New registration** > Name: `EnGen-Publisher-Service`.
3. Supported account types: "Single tenant".
4. **Register**.

### Step 1.2: Generate Client Secret
1. **Certificates & secrets** > **+ New client secret**.
2. Description: `EnGen-Publishing-Key`.
3. **Add**.
4. **⚠️ CRITICAL**: Copy the **Value** immediately. It maps to `AZURE_CLIENT_SECRET`.

### Step 1.3: Configure API Permissions
*The Publisher requires write access to create pages.*

1. **API permissions** > **+ Add a permission** > **Microsoft Graph**.
2. **Application permissions** (NOT Delegated).
3. Search for and check these specific permissions:
   - `Sites.ReadWrite.All` (Required to create and edit pages).
   - `Sites.Manage.All` (Often required for publishing/promoting pages).
4. **Add permissions**.

### Step 1.4: Grant Admin Consent
1. Look for the "Not granted..." warning.
2. Click **Grant admin consent for [Organization]**.
3. Verify the status column shows green checkmarks.

### Step 1.5: Capture IDs
From the **Overview** blade, copy:
- `AZURE_CLIENT_ID` (Application ID)
- `AZURE_TENANT_ID` (Directory ID)

---

## 2. SharePoint Environment Setup

The publisher creates "Modern Pages" in the **Site Pages** library.

### Step 2.1: Target Site Preparation
1. **Identify Site**: Determine which site will host the generated documentation (e.g., `https://contoso.sharepoint.com/sites/ArchitecturePatterns`).
2. **Site Pages Library**: Ensure the "Site Pages" library exists (it exists by default on modern Team and Communication sites).
3. **Folder Creation (Optional)**: If you want to publish to a specific folder (e.g., "GeneratedDocs"), you generally create this folder manually within "Site Pages" first to ensure permissions are clean, although the code may attempt to create it.

### Step 2.2: Retrieve Site ID
You need the **Site ID** to tell the API where to post.

**Find the Site ID (`SHAREPOINT_SITE_ID`)**
Use Microsoft Graph Explorer (https://developer.microsoft.com/graph/graph-explorer):
```http
GET https://graph.microsoft.com/v1.0/sites/{hostname}:/{relative-path}
# Example: https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/ArchitecturePatterns
```
*Copy the `id` string (it usually looks like `hostname,guid,guid`).*

---

## 3. Configuration & Execution

The publisher code looks for specific environment variables. Create or update the `.env` file in `inference-service/.env`.

### Step 3.1: Environment Variables

```ini
# --- Publisher Credentials ---
# From Entra ID (Step 1.5 & 1.2)
AZURE_TENANT_ID=00000000-0000-0000-0000-000000000000
AZURE_CLIENT_ID=00000000-0000-0000-0000-000000000000
AZURE_CLIENT_SECRET=xxx_Your_Secret_Value_xxx

# --- Target Configuration ---
# From Graph Explorer (Step 2.2)
SHAREPOINT_SITE_ID=contoso.sharepoint.com,0000-0000,0000-0000

# Optional Settings (Defaults usually work)
# SHAREPOINT_TARGET_FOLDER=Generated Patterns
# SHAREPOINT_PROMOTE_AS_NEWS=true
```

## Troubleshooting Common Errors

| Error | Cause | Fix |
| :--- | :--- | :--- |
| `401 Unauthorized` | Invalid Secret or Tenant ID. | Check `.env` values. Ensure Secret didn't expire. |
| `403 Forbidden` | Missing Permissions. | Ensure `Sites.ReadWrite.All` is added AND **Admin Consent** is granted. |
| `ResourceNotFound` | Wrong Site ID. | Re-check the Site ID in Graph Explorer. |
| `NameResolutionFailure` | Bad Hostname. | Ensure your SharePoint URL in the Site ID is correct. |

---

## Implementation Details (For Developers)

- **Web Parts**: The publisher converts Markdown to HTML and wraps it in a standard `RTE` (Rich Text Editor) web part.
- **Publishing State**: Pages are created in `Draft` state. The `publish_page` method must be called to make them visible to all users.
- **Images**: If the Markdown contains images, they must be publicly accessible or hosted in SharePoint. The current `Streamlit` app workflow typically bypasses image embedding in the *published* page unless specific logic uploads them to the Site Assets library first.
