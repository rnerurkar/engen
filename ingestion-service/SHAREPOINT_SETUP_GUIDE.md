# SharePoint & Entra ID Setup Guide for EnGen Ingestion

**Scope**: Configuration required to enable the `sharepoint.py` client to extract modern pages and images from SharePoint Online for the EnGen Ingestion Service.

---

## 1. Microsoft Entra ID (Azure AD) Configuration

The Ingestion Service runs as a background process using the **Client Credentials Flow**. It requires a registered application identity to authenticate against Microsoft Graph API without user interaction.

### Step 1.1: Register the Application
1. Navigate to the [Azure Portal](https://portal.azure.com) > **Microsoft Entra ID**.
2. Select **App registrations** from the left menu.
3. Click **+ New registration**.
   - **Name**: `EnGen-Ingestion-Service` (or similar).
   - **Supported account types**: Select "Accounts in this organizational directory only (Single tenant)".
   - **Redirect URI**: Leave blank (not needed for daemon apps).
4. Click **Register**.

### Step 1.2: Generate Client Secret
*This secret acts as the "password" for the application.*
1. In your new app registration, go to **Certificates & secrets**.
2. Click **+ New client secret**.
3. **Description**: `EnGen-Ingestion-Key`.
4. **Expires**: Select a duration (e.g., 12 months).
5. Click **Add**.
6. **⚠️ IMPORTANT**: Copy the **Value** immediately. It will be hidden later.
   - *This maps to `AZURE_CLIENT_SECRET` in your .env file.*

### Step 1.3: Configure API Permissions
*Grant the application read access to SharePoint.*
1. Go to **API permissions**.
2. Click **+ Add a permission**.
3. Select **Microsoft Graph**.
4. Click **Application permissions** (NOT Delegated permissions).
5. Search for and check: `Sites.Read.All`.
6. Click **Add permissions**.

### Step 1.4: Grant Admin Consent
*Permissions are not active until an Admin enables them.*
1. On the API permissions screen, look for the warning: "Not granted for...".
2. Click the **Grant admin consent for [Your Organization]** button.
3. Confirm that the status column changes to a green checkmark.

### Step 1.5: Capture IDs
Go to the **Overview** blade of your app registration and copy:
- **Application (client) ID** -> maps to `AZURE_CLIENT_ID`.
- **Directory (tenant) ID** -> maps to `AZURE_TENANT_ID`.

---

## 2. SharePoint Environment Setup

The ingestion code logic relies on specific data structures (Modern Pages) and API identifiers.

### Step 2.1: Site Content Structure
1. **Modern Pages Only**: Ensure your architecture patterns are created as "Site Pages" (New > Page).
   - *Why*: The extractor specifically requests the `CanvasContent1` field, which contains the rich HTML of modern pages. It will not work with Wiki pages or uploaded Word documents.
2. **Embedded Diagrams**: Images should be inserted directly into the page canvas.
   - *Why*: The extractor parses `<img>` tags within the HTML to find and download diagrams for the Gemini Vision analysis.

### Step 2.2: Retrieve Resource IDs
You need the GUIDs for the specific Site and List to configure the `.env` file. You can find these using the [Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer) (sign in with your work account).

**A. Find the Site ID (`SP_SITE_ID`)**
Run a GET request with your site's hostname and relative path:
```http
GET https://graph.microsoft.com/v1.0/sites/{hostname}:/{relative-path}
# Example: https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/ArchitectureCenter
```
*Copy the `id` value from the response.*

**B. Find the List ID (`SP_LIST_ID`)**
Run a GET request using the Site ID you just found to list libraries:
```http
GET https://graph.microsoft.com/v1.0/sites/{site-id}/lists
```
*Search the JSON response for the list with `"displayName": "Site Pages"`. Copy its `id`.*

---

## 3. Local Environment Configuration

Update your `ingestion-service/.env` file with the values collected above.

```ini
# --- SharePoint Configuration ---

# From Entra ID (Step 1.5)
AZURE_TENANT_ID=00000000-0000-0000-0000-000000000000
AZURE_CLIENT_ID=00000000-0000-0000-0000-000000000000

# From Entra ID (Step 1.2)
AZURE_CLIENT_SECRET=xxx_Your_Secret_Value_xxx

# From Graph Explorer (Step 2.2)
SP_SITE_ID=contoso.sharepoint.com,0000-0000,0000-0000
SP_LIST_ID=00000000-0000-0000-0000-000000000000
```

---

## Troubleshooting

- **401 Unauthorized**: Usually means `AZURE_CLIENT_SECRET` is wrong or expired.
- **403 Forbidden**: Usually means "Admin Consent" was not granted in Step 1.4.
- **"CanvasContent1" not found**: The target page is likely a classic Web Part page or Wiki page. Ensure it is a Modern SharePoint Page.
